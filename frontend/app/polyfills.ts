"use client";

// Immediate execution
(function () {
    if (typeof Promise.withResolvers === 'undefined') {
        const polyfill = function () {
            let resolve, reject;
            const promise = new Promise((res, rej) => {
                resolve = res;
                reject = rej;
            });
            return { promise, resolve, reject };
        };

        if (typeof window !== 'undefined') {
            // @ts-ignore
            window.Promise.withResolvers = polyfill;
        } else {
            // @ts-ignore
            global.Promise.withResolvers = polyfill;
        }
    }
})();

if (typeof Promise.withResolvers === 'undefined') {
    if (typeof window !== 'undefined') {
        // @ts-ignore
        window.Promise.withResolvers = function () {
            let resolve, reject;
            const promise = new Promise((res, rej) => {
                resolve = res;
                reject = rej;
            });
            return { promise, resolve, reject };
        };
    } else {
        // @ts-ignore
        global.Promise.withResolvers = function () {
            let resolve, reject;
            const promise = new Promise((res, rej) => {
                resolve = res;
                reject = rej;
            });
            return { promise, resolve, reject };
        };
    }
}
