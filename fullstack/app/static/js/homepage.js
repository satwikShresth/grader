document.addEventListener("DOMContentLoaded", function () {
  const submitBtn = document.getElementById("submitBtn");
  const groupSubmitBtn = document.getElementById("groupSubmitBtn");
  const form = document.getElementById("uploadForm");
  const groupForm = document.getElementById("groupUploadForm");
  const requiredFields = form.querySelectorAll("[required]");
  const groupRequiredFields = groupForm.querySelectorAll("[required]");

  function checkFormCompletion() {
    let allFilled = true;
    requiredFields.forEach(function (field) {
      if (!field.value || (field.type === "file" && field.files.length === 0)) {
        allFilled = false;
      }
    });

    if (allFilled) {
      submitBtn.disabled = false;
      submitBtn.classList.add("enabled");
    } else {
      submitBtn.disabled = true;
      submitBtn.classList.remove("enabled");
    }
  }

  function checkGroupFormCompletion() {
    let allFilled = true;
    groupRequiredFields.forEach(function (field) {
      if (!field.value || (field.type === "file" && field.files.length === 0)) {
        allFilled = false;
      }
    });

    if (allFilled) {
      groupSubmitBtn.disabled = false;
      groupSubmitBtn.classList.add("enabled");
    } else {
      groupSubmitBtn.disabled = true;
      groupSubmitBtn.classList.remove("enabled");
    }
  }

  requiredFields.forEach(function (field) {
    field.addEventListener("input", checkFormCompletion);
    field.addEventListener("change", checkFormCompletion);
  });

  groupRequiredFields.forEach(function (field) {
    field.addEventListener("input", checkGroupFormCompletion);
    field.addEventListener("change", checkGroupFormCompletion);
  });
});
