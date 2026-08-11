/* Ejari Helper — guide table of contents.
   Builds an "On this page" list from the guide's h2 headings.
   Collapsible on mobile; pinned beside the column on wide screens. */
(function () {
  'use strict';
  var main = document.querySelector('main');
  if (!main) return;
  var heads = Array.prototype.slice.call(main.querySelectorAll('h2'));
  if (heads.length < 3) return;

  var isAr = document.documentElement.lang === 'ar';
  var used = {};
  function slugify(s) {
    var slug = s.toLowerCase().trim()
      .replace(/[^a-z0-9؀-ۿ]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 60) || 'section';
    var out = slug, n = 2;
    while (used[out]) out = slug + '-' + n++;
    used[out] = true;
    return out;
  }

  var nav = document.createElement('nav');
  nav.className = 'eh-toc';
  nav.setAttribute('aria-label', isAr ? 'المحتويات' : 'Contents');
  var box = document.createElement('details');
  box.className = 'eh-toc-box';
  var summary = document.createElement('summary');
  summary.textContent = isAr ? 'المحتويات' : 'On this page';
  box.appendChild(summary);
  var ol = document.createElement('ol');
  heads.forEach(function (h) {
    if (!h.id) h.id = slugify(h.textContent);
    var li = document.createElement('li');
    var a = document.createElement('a');
    a.href = '#' + h.id;
    a.textContent = h.textContent.trim();
    li.appendChild(a);
    ol.appendChild(li);
  });
  box.appendChild(ol);
  nav.appendChild(box);
  if (window.matchMedia('(min-width:1240px)').matches) box.setAttribute('open', '');

  var intro = main.querySelector('.guide-intro');
  if (intro && intro.parentNode) intro.parentNode.insertBefore(nav, intro.nextSibling);
  else main.insertBefore(nav, main.firstChild);
})();
