// Swap the sticky chart when a new chapter enters the viewport center
const chapters = document.querySelectorAll(".chapter");

const chapterObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const chartKey = entry.target.dataset.chart;
      if (CHART_RENDERERS[chartKey]) CHART_RENDERERS[chartKey]();
    }
  });
}, { rootMargin: "-45% 0px -45% 0px", threshold: 0 });

chapters.forEach(ch => chapterObserver.observe(ch));

// Activate highlighter marks + step callouts as they scroll into view
const markObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) entry.target.classList.add("is-marked");
  });
}, { threshold: 0.8 });

document.querySelectorAll("mark").forEach(m => markObserver.observe(m));

const stepObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    entry.target.classList.toggle("is-active", entry.isIntersecting);
  });
}, { rootMargin: "-40% 0px -40% 0px", threshold: 0 });

document.querySelectorAll(".step").forEach(s => stepObserver.observe(s));
