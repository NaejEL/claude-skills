import argparse


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--tokens', type=int, default=512)
    return p.parse_args()
