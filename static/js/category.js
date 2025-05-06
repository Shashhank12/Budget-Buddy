function make_editable(index) {
    const span = document.getElementById(`category-${index}`);
    const input = document.getElementById(`input-${index}`);
    span.setAttribute("contenteditable", "true");
    span.focus();

    span.addEventListener('blur', function() {
      input.value = span.innerText.trim();
    });
  }
