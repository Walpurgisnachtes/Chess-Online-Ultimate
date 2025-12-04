$(document).ready(function () {
  (() => {
    const preferredTheme = localStorage.getItem("theme");
    const themeToggle = $("#theme-toggle");

    const icon = themeToggle.find("i");
    const span = themeToggle.find("span");

    if (preferredTheme == "dark") {
      span.removeClass("text-dark").addClass("text-light");
      span.text("Day Mode");
      icon.removeClass("fa-moon").addClass("fa-sun text-warning");
    } else {
      span.removeClass("text-light").addClass("text-dark");
      span.text("Night Mode");
      icon.removeClass("fa-sun text-warning").addClass("fa-moon");
    }
  })();

  $("#theme-toggle").click(function () {
    const icon = $(this).find("i");
    const span = $(this).find("span");

    if (icon.hasClass("fa-moon")) {
      span.removeClass("text-dark").addClass("text-light");
      span.text("Day Mode");
      icon.removeClass("fa-moon").addClass("fa-sun text-warning");
    } else {
      span.removeClass("text-light").addClass("text-dark");
      span.text("Night Mode");
      icon.removeClass("fa-sun text-warning").addClass("fa-moon");
    }
  });
});
