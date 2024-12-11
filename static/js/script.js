const video = document.getElementById("webcam");
const imagePreview = document.getElementById("imagePreview");
const matchBtn = document.getElementById("matchBtn");
const captureBtn = document.getElementById("captureBtn");
const loadingSpinner = document.getElementById("loading");
let currentBlob = null;
let currentStream = null;
let currentFile = null;

function startWebcam() {
  if (currentStream) {
    currentStream.getTracks().forEach((track) => track.stop());
    currentStream = null;
    video.srcObject = null;
  }

  navigator.mediaDevices
    .getUserMedia({ video: true })
    .then((stream) => {
      currentStream = stream;
      video.srcObject = stream;
      video.style.display = "block";
      imagePreview.style.display = "none";
      matchBtn.style.display = "none";
      captureBtn.innerHTML = '<i class="fas fa-camera"></i> Capture Image';

      imagePreview.src = "";
    })
    .catch((error) => alert("Webcam not accessible. Error: " + error));
}

function captureImage() {
  video.pause();

  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  if (currentStream) {
    currentStream.getTracks().forEach((track) => {
      track.stop();
    });

    video.srcObject = null;
    currentStream = null;
  }

  video.style.display = "none";
  imagePreview.src = canvas.toDataURL("image/jpeg");
  imagePreview.style.display = "block";

  captureBtn.innerHTML = '<i class="fas fa-camera"></i> Open Camera';

  canvas.toBlob((blob) => {
    currentBlob = blob;
    currentFile = null;
    matchBtn.style.display = "flex";
  });
}

function previewUploadedImage(event) {
  const file = event.target.files[0];
  if (file) {
    const validExtensions = ["jpeg", "jpg", "png", "heic"];
    const fileExtension = file.name.split(".").pop().toLowerCase();

    if (!validExtensions.includes(fileExtension)) {
      alert("Invalid file type. Please upload an image.");
      return;
    }

    if (currentStream) {
      currentStream.getTracks().forEach((track) => track.stop());
      currentStream = null;
      video.srcObject = null;
      video.style.display = "none";
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      imagePreview.src = e.target.result;
      video.style.display = "none";
      imagePreview.style.display = "block";

      captureBtn.innerHTML = '<i class="fas fa-camera"></i> Open Camera';

      currentFile = file;
      currentBlob = null;
      matchBtn.style.display = "flex";
    };
    reader.readAsDataURL(file);
  }
}

function sendImage() {
  const errorText = document.querySelector("#errorText");
  if (!currentBlob && !currentFile) {
    alert("Please capture or upload an image first.");
    return;
  }

  loadingSpinner.style.display = "block";
  matchBtn.disabled = true;
  matchBtn.innerHTML = `
    <i class="fas fa-search"></i> Matching...
  `;

  const formData = new FormData();

  if (currentFile) {
    formData.append("file", currentFile, currentFile.name);
  } else {
    formData.append("file", currentBlob, "captured_image.jpg");
  }

  fetch("http://localhost:8000/process-image/", {
    method: "POST",
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      displayResults(data);
      loadingSpinner.style.display = "none";
      matchBtn.innerHTML = `
        <i class="fas fa-search"></i> Match
      `;
      matchBtn.disabled = false;
    })
    .catch((error) => {
      errorText.innerText = error.message;
      loadingSpinner.style.display = "none";
      matchBtn.innerHTML = `
        <i class="fas fa-search"></i> Match
      `;
      matchBtn.disabled = false;
    });
}

function displayResults(data) {
  const matchedImagesTable = document.querySelector("#matched-images tbody");
  const result = document.querySelector("#result");
  matchedImagesTable.innerHTML = "";

  if (data.message === "No matches found") {
    result.style.color = "red";
    result.innerText = data.message;
  } else {
    result.innerText = `Total ${data.matches.length} images matched`;

    data.matched_images.forEach((imgPath, index) => {
      const accuracy = data.accuracy[index];
      const title = data.matches[index] || `Person ${index + 1}`;
      const accuracyPercentage = Math.round(accuracy);
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${index + 1}</td>
        <td><img src="${imgPath}" alt="Matched Image" /></td>
        <td>${title}</td>
        <td>
          ${accuracyPercentage}%
          <div class="accuracy-bar">
            <span style="width: ${accuracyPercentage}%;"></span>
          </div>
        </td>
      `;
      matchedImagesTable.appendChild(row);
    });
  }
}

captureBtn.addEventListener("click", function () {
  if (video.style.display === "block") {
    captureImage();
  } else {
    startWebcam();
  }
});
