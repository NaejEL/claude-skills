# Sequences gh/git deterministes de ship-pr (D11).
#
# - SP-11 : preflight, dans l'ordre, arret sur le premier echec avec le message
#   prevu ; etat de l'arbre de travail et owner/repo.
# - SP-12 : upstream absent ou commits non pousses -> git push -u origin HEAD.
# - SP-13 : recherche d'une PR ouverte branche -> cible, sinon creation.
# - SP-14 : etat de la PR (headRefOid, mergeable, mergeStateStatus).
# - SP-15 : collecte du diff de la ronde (ronde 1 : gh pr diff ; ensuite :
#   git diff <HEAD d'avant le correctif de la ronde precedente>..HEAD, donc le
#   commit de correctif, + fichiers deja signales).
# - SP-16 : commentaire inline avec le headRefOid relu au moment du post ;
#   sur HTTP 422 seulement, repli niveau fichier puis, en dernier recours,
#   commentaire de PR. Toute autre erreur arrete le skill.
# - SP-17 : un commit par ronde "fix(review): corrections round N — <resume>",
#   puis push simple (jamais d'amend, jamais de force-push).
# - SP-18 : reponse et resolution des threads des findings corriges ; threads
#   des findings non corriges : reponse avec la raison, laisses ouverts.
# - SP-19 : merge par commit de merge et suppression de la branche, refuse si un
#   theme n'est pas couvert ou si la boucle n'est pas terminee.
# - D3 : ajout de .claude/runs/ a .git/info/exclude, idempotent.

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import registry as registry_mod, shippr
from .proc import Result

HTTP_422 = re.compile(r"\bHTTP 422\b")   # message de gh : "... (HTTP 422)"

Run = Callable[..., Result]
EXCLUDE_LINE = ".claude/runs/"

MSG_GH_AUTH = "gh non authentifié — lancer `gh auth login`"
MSG_NO_GITHUB = "pas de remote GitHub"
MSG_ON_TARGET = "vous êtes déjà sur {target}, placez-vous sur la branche à merger"
MSG_NO_TARGET = "la branche cible {target} n'existe pas sur origin"

THREADS_QUERY = (
    "query($owner:String!,$repo:String!,$number:Int!){"
    " repository(owner:$owner,name:$repo){ pullRequest(number:$number){"
    " reviewThreads(first:100){ nodes{ id isResolved"
    " comments(first:10){ nodes{ databaseId } } } } } } }"
)
RESOLVE_MUTATION = (
    "mutation($t:ID!){ resolveReviewThread(input:{threadId:$t}){ thread{ id isResolved } } }"
)


class Stop(RuntimeError):
    """Arret explicite : le message est destine a l'utilisateur."""


def _must(res: Result, what: str) -> Result:
    if not res.ok:
        raise Stop("%s a echoue : %s" % (what, (res.err or res.out).strip()))
    return res


def preflight_checks(run: Run, target: str) -> Dict[str, Any]:
    """SP-11, etapes 1 a 4 du preflight."""
    if not run(["gh", "auth", "status"]).ok:
        raise Stop(MSG_GH_AUTH)
    remote = run(["git", "remote", "get-url", "origin"])
    if not remote.ok or "github.com" not in remote.out:
        raise Stop(MSG_NO_GITHUB)
    branch = _must(run(["git", "rev-parse", "--abbrev-ref", "HEAD"]), "git rev-parse").out.strip()
    if branch == target:
        raise Stop(MSG_ON_TARGET.format(target=target))
    fetched = run(["git", "fetch", "origin", target])
    if not fetched.ok or not run(["git", "rev-parse", "--verify", "origin/" + target]).ok:
        raise Stop(MSG_NO_TARGET.format(target=target))
    return {"branch": branch}


def worktree_and_repo(run: Run) -> Dict[str, Any]:
    """SP-11, etapes 5 (constat seulement, la gate reste au prompt) et 7."""
    status = _must(run(["git", "status", "--porcelain"]), "git status").out
    repo = _must(run(["gh", "repo", "view", "--json", "owner,name", "-q",
                      '.owner.login + "/" + .name']), "gh repo view").out.strip()
    dirty = [line for line in status.splitlines() if line.strip()]
    return {"dirty": bool(dirty), "dirty_files": dirty, "owner_repo": repo}


def ensure_exclude(run: Run, root: Path) -> bool:
    """D3 : ajoute .claude/runs/ a .git/info/exclude s'il n'y est pas. Rend True si ajoute."""
    rel = _must(run(["git", "rev-parse", "--git-path", "info/exclude"]), "git rev-parse").out.strip()
    path = Path(rel)
    if not path.is_absolute():
        path = Path(root) / path
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if any(line.strip() == EXCLUDE_LINE for line in text.splitlines()):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    if text and not text.endswith("\n"):
        text += "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text + EXCLUDE_LINE + "\n")
    return True


def sync_upstream(run: Run) -> Dict[str, Any]:
    """SP-12."""
    upstream = run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    push = not upstream.ok
    if not push:
        ahead = _must(run(["git", "rev-list", "@{u}..HEAD", "--count"]), "git rev-list").out.strip()
        push = int(ahead or "0") > 0
    if push:
        _must(run(["git", "push", "-u", "origin", "HEAD"]), "git push -u origin HEAD")
    return {"pushed": push}


def pr_state(run: Run, number: int) -> Dict[str, Any]:
    """SP-14."""
    res = _must(run(["gh", "pr", "view", str(number), "--json",
                     "headRefOid,mergeable,mergeStateStatus"]), "gh pr view")
    data = json.loads(res.out)
    data["conflicting"] = data.get("mergeable") == "CONFLICTING"
    return data


def find_or_create_pr(run: Run, state: Dict[str, Any], title: Optional[str] = None,
                      body: Optional[str] = None) -> Dict[str, Any]:
    """SP-13 : reprend la PR ouverte, sinon la cree si titre et corps sont fournis."""
    target, branch = state["target"], state["branch"]
    res = _must(run(["gh", "pr", "list", "--head", branch, "--base", target, "--state", "open",
                     "--json", "number,url,title"]), "gh pr list")
    prs = json.loads(res.out or "[]")
    created = False
    if prs:
        number, url = prs[0]["number"], prs[0]["url"]
    elif title is None or body is None:
        log = _must(run(["git", "log", "origin/%s..HEAD" % target, "--oneline"]), "git log").out
        stat = _must(run(["git", "diff", "origin/%s...HEAD" % target, "--stat"]), "git diff --stat").out
        return {"number": None, "log": log, "stat": stat}
    else:
        _must(run(["gh", "pr", "create", "--base", target, "--title", title, "--body", body]), "gh pr create")
        view = json.loads(_must(run(["gh", "pr", "view", "--json", "number,url"]), "gh pr view").out)
        number, url, created = view["number"], view["url"], True
    state["pr"], state["url"] = number, url
    result = {"number": number, "url": url, "created": created}
    result.update(pr_state(run, number))
    return result


def collect_diff(run: Run, state: Dict[str, Any]) -> str:
    """SP-15."""
    if state["round"] == 1 or not state.get("prev_round_sha"):
        return _must(run(["gh", "pr", "diff", str(state["pr"])]), "gh pr diff").out
    out = _must(run(["git", "diff", "%s..HEAD" % state["prev_round_sha"]]), "git diff").out
    flagged = sorted({c["file"] for c in state["candidates"].values() if c["status"] == "CONFIRMED"})
    if flagged:
        out += _must(run(["git", "diff", "origin/%s...HEAD" % state["target"], "--"] + flagged),
                     "git diff fichiers signales").out
    return out


def comment_body(c: Dict[str, Any]) -> str:
    return "**[%s] %s**\n\n%s\n\nCorrection suggérée : %s" % (
        c["severity"], c["title"], c["description"], c["fix"])


def post_comment(run: Run, state: Dict[str, Any], fid: str) -> Dict[str, Any]:
    """SP-16."""
    c = state["candidates"].get(fid)
    if c is None or c["status"] != "CONFIRMED":
        raise Stop("seul un finding CONFIRMED est poste : %s" % fid)
    sha = pr_state(run, state["pr"])["headRefOid"]
    base = ["gh", "api", "repos/%s/pulls/%d/comments" % (state["owner_repo"], state["pr"]),
            "-f", "body=" + comment_body(c), "-f", "commit_id=" + sha, "-f", "path=" + c["file"]]
    res = run(base + ["-F", "line=%d" % c["line"], "-f", "side=" + c.get("side", "RIGHT")])
    mode = "inline"
    if not res.ok:
        if not HTTP_422.search(res.err + res.out):
            raise Stop("commentaire inline refuse (hors HTTP 422) : %s" % (res.err or res.out).strip())
        res = run(base + ["-f", "subject_type=file"])
        mode = "file"
    if res.ok:
        c["comment_id"] = json.loads(res.out)["id"]
        return {"finding": fid, "mode": mode, "comment_id": c["comment_id"], "commit_id": sha}
    body = "%s\n\n(%s, ligne %d)" % (comment_body(c), c["file"], c["line"])
    _must(run(["gh", "pr", "comment", str(state["pr"]), "--body", body]), "gh pr comment")
    return {"finding": fid, "mode": "pr", "comment_id": None, "commit_id": sha}


def commit_round(run: Run, state: Dict[str, Any], reg: registry_mod.Registry, summary: str,
                 fixed: List[str], not_fixed: Dict[str, str]) -> Dict[str, Any]:
    """SP-17 et SP-09."""
    ids = fixed + list(not_fixed)
    doubles = sorted({fid for fid in ids if ids.count(fid) > 1})
    if doubles:
        raise Stop("finding(s) consigne(s) deux fois : %s" % ", ".join(doubles))
    for fid in ids:
        c = state["candidates"].get(fid)
        if c is None or c["round"] != state["round"] or c["status"] != "CONFIRMED" or c["outcome"]:
            raise Stop("%s n'est pas un finding CONFIRMED en attente de la ronde courante" % fid)
    commit = None
    if fixed:
        pre = _must(run(["git", "rev-parse", "HEAD"]), "git rev-parse").out.strip()
        shippr.mark_pre_fix(state, pre)
        message = "fix(review): corrections round %d — %s" % (state["round"], summary.strip())
        _must(run(["git", "add", "-A"]), "git add -A")
        _must(run(["git", "commit", "-m", message]), "git commit")
        _must(run(["git", "push"]), "git push")
        commit = _must(run(["git", "rev-parse", "HEAD"]), "git rev-parse").out.strip()
        state["commits"].append({"round": state["round"], "hash": commit, "summary": summary.strip()})
    for fid in fixed:
        shippr.set_outcome(state, reg, fid, True, commit=commit)
    for fid, reason in not_fixed.items():
        shippr.set_outcome(state, reg, fid, False, reason=reason)
    return {"commit": commit, "fixed": fixed, "not_fixed": list(not_fixed)}


def handle_threads(run: Run, state: Dict[str, Any]) -> Dict[str, Any]:
    """SP-18."""
    owner, repo = state["owner_repo"].split("/", 1)
    res = _must(run(["gh", "api", "graphql", "-f", "query=" + THREADS_QUERY, "-f", "owner=" + owner,
                     "-f", "repo=" + repo, "-F", "number=%d" % state["pr"]]), "gh api graphql")
    nodes = json.loads(res.out)["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    thread_of = {}
    for node in nodes:
        for com in node["comments"]["nodes"]:
            thread_of[com["databaseId"]] = node["id"]
    resolved, left_open = [], []
    for c in state["candidates"].values():
        if c["round"] != state["round"] or c["outcome"] is None or c["thread_done"] or c["comment_id"] is None:
            continue
        replies = "repos/%s/pulls/%d/comments/%d/replies" % (state["owner_repo"], state["pr"], c["comment_id"])
        if c["outcome"] == "FIXED":
            _must(run(["gh", "api", replies, "-f", "body=Corrigé dans %s." % c["commit"]]), "reponse au thread")
            thread = thread_of.get(c["comment_id"])
            if thread is None:
                raise Stop("thread introuvable pour le commentaire %s" % c["comment_id"])
            _must(run(["gh", "api", "graphql", "-f", "query=" + RESOLVE_MUTATION, "-f", "t=" + thread]),
                  "resolution du thread")
            resolved.append(c["id"])
        else:
            _must(run(["gh", "api", replies, "-f", "body=" + c["reason"]]), "reponse au thread")
            left_open.append(c["id"])
        c["thread_done"] = True
    return {"resolved": resolved, "left_open": left_open}


def merge(run: Run, state: Dict[str, Any], check_only: bool) -> Dict[str, Any]:
    """SP-19 et SP-05."""
    refusal = shippr.merge_refusal(state)
    if refusal:
        raise Stop(refusal)
    if check_only:
        result = shippr.summary(state)
        result["pr_state"] = pr_state(run, state["pr"])
        return result
    _must(run(["gh", "pr", "merge", str(state["pr"]), "--merge", "--delete-branch"]), "gh pr merge")
    _must(run(["git", "checkout", state["target"]]), "git checkout")
    _must(run(["git", "pull"]), "git pull")
    state["merged"] = True
    return {"merged": True, "pr": state["pr"], "target": state["target"]}
