'use strict';

function sum(values) {
    return values.reduce((acc, v) => acc + v, 0);
}

module.exports = { sum };
