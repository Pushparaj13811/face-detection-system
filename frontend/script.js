const video = document.getElementById("webcam");
const imagePreview = document.getElementById("imagePreview");
const matchBtn = document.getElementById("matchBtn");
const captureBtn = document.getElementById("captureBtn");
let currentBlob = null;
let currentStream = null;

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
    matchBtn.style.display = "flex";
  });
}

function previewUploadedImage(event) {
  const file = event.target.files[0];
  if (file) {
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

      const reader2 = new FileReader();
      reader2.onloadend = () => {
        currentBlob = new Blob([reader2.result]);
        matchBtn.style.display = "flex";
      };
      reader2.readAsArrayBuffer(file);
    };
    reader.readAsDataURL(file);
  }
}

function sendImage() {
  const errorText = document.querySelector("#errorText");
  if (!currentBlob) {
    alert("Please capture or upload an image first.");
    return;
  }

  // Show spinner and update button text
  matchBtn.innerHTML = `
          <i class="fas fa-search"></i>
          Matching...
          <span class="spinner"></span>
        `;
  matchBtn.disabled = true;

  const formData = new FormData();
  formData.append("file", currentBlob, "uploaded_image.jpg");

  fetch("http://localhost:8000/process-image/", {
    method: "POST",
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      displayResults(data);
      matchBtn.innerHTML = `
              <i class="fas fa-search"></i>
              Match
            `;
      matchBtn.disabled = false;
    })
    .catch((error) => {
      errorText.innerText = error.message;
      matchBtn.innerHTML = `
              <i class="fas fa-search"></i>
              Match
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
    data.matched_images.forEach((imgBase64, index) => {
      result.innerText = `Total ${data.matches.length} images matched`;
      const accuracy = data.accuracy[index];
      const title = data.matches[index] || `Person ${index + 1}`;
      const accuracyPercentage = Math.round(accuracy);

      const row = document.createElement("tr");
      row.innerHTML = `
            <td>${index + 1}</td>
            <td><img src="data:image/jpeg;base64,${imgBase64}" /></td>
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
