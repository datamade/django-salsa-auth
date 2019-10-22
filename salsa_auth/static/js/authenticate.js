var authCookie = {
    maxAgeToGMT: function(nMaxAge) {
        // IE, Edge, and mobile shim
        // See: https://developer.mozilla.org/en-US/docs/Web/API/Document/cookie/Simple_document.cookie_framework
        return nMaxAge === Infinity ? "Fri, 31 Dec 9999 23:59:59 GMT" : (new Date(nMaxAge * 1e3 + Date.now())).toUTCString();
    },
    setAuthorization: function(cookieName, cookieDomain) {
        docCookies.setItem(cookieName, "true", authCookie.maxAgeToGMT(Infinity), '/', cookieDomain);
    },
    getAuthorization: function(cookieName) {
        return docCookies.getItem(cookieName) == 'true';
    }
};
