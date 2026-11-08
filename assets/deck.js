(() => {
  'use strict';
  const slides = [...document.querySelectorAll('.slide')];
  const notes = [...document.querySelectorAll('.note')];
  const stage = document.querySelector('#stage');
  let index = 0;
  function resize() {
    const available = innerWidth * (document.body.classList.contains('notes-on') ? .57 : 1);
    const scale = Math.min(available / 1600, innerHeight / 900);
    stage.style.transform = `scale(${scale})`;
    stage.style.left = `${(available - 1600 * scale) / 2}px`;
    stage.style.top = `${(innerHeight - 900 * scale) / 2}px`;
  }
  function show(n, updateHash = true) {
    index = Math.min(slides.length - 1, Math.max(0, n));
    slides.forEach((slide, i) => {
      slide.classList.toggle('active', i === index);
      slide.setAttribute('aria-hidden', i !== index ? 'true' : 'false');
      slide.inert = i !== index;
    });
    notes.forEach((note, i) => note.classList.toggle('active', i === index));
    document.querySelector('#counter').textContent = `${index + 1} / ${slides.length}`;
    document.querySelector('#previous').disabled = index === 0;
    document.querySelector('#next').disabled = index === slides.length - 1;
    document.querySelector('#live-status').textContent = `Слайд ${index + 1}: ${slides[index].querySelector('h1').textContent}`;
    if (updateHash) history.replaceState(null, '', `#slide-${String(index + 1).padStart(2, '0')}`);
    document.querySelector('.notes-panel').scrollTop = 0;
  }
  function fromHash() {
    const n = Number(location.hash.replace('#slide-', ''));
    show(Number.isFinite(n) && n > 0 ? n - 1 : 0, false);
  }
  function toggleNotes() {
    document.body.classList.toggle('notes-on');
    document.querySelector('#toggle-notes').setAttribute('aria-pressed', document.body.classList.contains('notes-on'));
    resize();
  }
  document.querySelector('#previous').onclick = () => show(index - 1);
  document.querySelector('#next').onclick = () => show(index + 1);
  document.querySelector('#toggle-notes').onclick = toggleNotes;
  document.querySelector('#fullscreen').onclick = () => {
    if (document.fullscreenElement) document.exitFullscreen();
    else document.documentElement.requestFullscreen().catch(() => {});
  };
  addEventListener('keydown', event => {
    if (event.altKey || event.ctrlKey || event.metaKey || /INPUT|TEXTAREA|SELECT/.test(event.target.tagName)) return;
    if (['ArrowRight', 'PageDown', ' '].includes(event.key) && !/BUTTON|A/.test(event.target.tagName)) { event.preventDefault(); show(index + 1); }
    if (['ArrowLeft', 'PageUp'].includes(event.key)) { event.preventDefault(); show(index - 1); }
    if (event.key === 'Home') { event.preventDefault(); show(0); }
    if (event.key === 'End') { event.preventDefault(); show(slides.length - 1); }
    if (event.key.toLowerCase() === 'n' || event.key.toLowerCase() === 'т') toggleNotes();
    if (event.key === 'Escape' && document.body.classList.contains('notes-on')) toggleNotes();
  });
  let hideTimer;
  addEventListener('pointermove', () => {
    document.body.classList.add('controls-visible');
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => document.body.classList.remove('controls-visible'), 1800);
  });
  addEventListener('resize', resize);
  addEventListener('hashchange', fromHash);
  fromHash(); resize();
})();
