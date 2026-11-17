/* Runs before first paint (loaded synchronously in <head>).
   Sets language/direction from localStorage to avoid a flash; external file so CSP needs no 'unsafe-inline'. */
(function () {
  try {
    var l = localStorage.getItem("haymanat-lang");
    if (l === "en" || l === "ar") {
      document.documentElement.lang = l;
      document.documentElement.dir = l === "ar" ? "rtl" : "ltr";
    }
  } catch (e) { /* storage unavailable */ }
  setTimeout(function () { document.documentElement.classList.remove("i18n-pending"); }, 2500);
})();
