/* Ejari Helper — shared page enhancements. */
(function () {
  'use strict';

  /* Click-to-load YouTube facade: swaps the poster button for the iframe
     only when the visitor asks for it. */
  document.querySelectorAll('.video-fac').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var id = btn.getAttribute('data-yt');
      if (!id) return;
      var iframe = document.createElement('iframe');
      iframe.src = 'https://www.youtube.com/embed/' + id + '?autoplay=1';
      iframe.title = btn.getAttribute('data-title') || 'Video';
      iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
      iframe.allowFullscreen = true;
      iframe.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;border:0';
      btn.replaceWith(iframe);
    });
  });
})();
