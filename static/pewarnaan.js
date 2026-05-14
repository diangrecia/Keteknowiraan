$(document).ready(function () {
  let selectedColorCodes = [];
  let selectedMotif = "";

  // ===== COLOR SCHEME ANALYZER VARIABLES =====
  let colorAnalysisVisible = false;
  let currentAnalysisData = null;
  let currentTaskId = null;

  const selectedColorsContainer = $("#selectedColorsContainer");
  const colorCounter = $("#colorCounter");
  const selectedColorsInput = $("#selectedColorsInput");
  const coloringForm = $("#coloringForm");
  const coloredImage = $("#coloredImage");
  const noImageMessage = $("#noImageMessage");
  const loadingSpinner = $("#loadingSpinner");
  const errorMessage = $("#errorMessage");
  const submitButton = $("#submitButton");
  const downloadImageBtn = $("#downloadImageBtn");
  const downloadPdfBtn = $("#downloadPdfBtn");
  const jenisUlosSelect = $("#jenisUlos");
  const motifCarouselContainer = $("#motifCarouselContainer");
  const motifCarousel = $("#motifCarousel");
  const selectedMotifInput = $("#selectedMotifInput");

  const usedColorsDisplay = $("#usedColorsDisplay");
  const actualUsedColorsPalette = $("#actualUsedColorsPalette");

  // ===== TAMBAHAN: ELEMEN UNTUK COLOR SCHEME RESULT =====
  const colorSchemeResult = $("#colorSchemeResult");
  const schemeRecommendation = $("#schemeRecommendation");

  // ===== COLOR SCHEME ANALYZER ELEMENTS =====
  const colorAnalysisSection = $("#colorAnalysisSection");
  const analysisContent = $("#analysisContent");
  const analysisPreview = $("#analysisPreview");
  const previewSchemeBtn = $("#previewSchemeBtn");
  const findSimilarBtn = $("#findSimilarBtn");
  const progressSection = $("#progressSection");
  const progressFill = $("#progressFill");
  const progressText = $("#progressText");
  const progressPercentage = $("#progressPercentage");
  const finalColorAnalysis = $("#finalColorAnalysis");
  const exportAnalysisBtn = $("#exportAnalysisBtn");

  // TAMBAHAN: Buat elemen loading bar dan tambahkan ke DOM setelah tombol submit
  const loadingBarHTML = `
        <div id="loadingBarContainer" class="loading-bar-container">
            <div id="loadingBarProgress" class="loading-bar-progress"></div>
            <div id="loadingBarText" class="loading-bar-text">0 %</div>
        </div>
    `;
  $("#submitButton").after(loadingBarHTML);

  // TAMBAHAN: Buat referensi ke elemen loading bar
  const loadingBarContainer = $("#loadingBarContainer");
  const loadingBarProgress = $("#loadingBarProgress");
  const loadingBarText = $("#loadingBarText");

  // TAMBAHAN: Fungsi untuk mengupdate progress bar
  function updateLoadingBar(percent) {
    loadingBarProgress.css("width", percent + "%");
    loadingBarText.text(percent + " %");
  }

  // ===== COLOR SCHEME ANALYZER FUNCTIONS =====
  function updateColorAnalysisProgress(percent) {
    if (progressFill.length) {
      progressFill.css("width", percent + "%");
    }
    if (progressPercentage.length) {
      progressPercentage.text(percent + "%");
    }
    
    // Update progress text berdasarkan percentage
    if (progressText.length) {
      let text = "Memproses...";
      if (percent < 5) text = "Menginisialisasi...";
      else if (percent < 15) text = "Memuat data Ulos...";
      else if (percent < 25) text = "Membuat fungsi objektif AI...";
      else if (percent < 90) text = "Menjalankan optimisasi algoritma...";
      else if (percent < 95) text = "Menganalisis skema warna...";
      else if (percent < 100) text = "Menyelesaikan hasil...";
      else text = "Selesai!";
      
      progressText.text(text);
    }
  }

  function toggleColorAnalysis() {
    colorAnalysisVisible = !colorAnalysisVisible;
    
    if (colorAnalysisVisible) {
      analysisContent.slideDown(300);
      $("#toggleAnalysisText").text("Sembunyikan Analisis");
      $("#toggleAnalysisBtn").removeClass("btn-outline-primary").addClass("btn-primary");
      
      // Auto preview jika ada warna yang dipilih
      if (selectedColorCodes.length >= 2) {
        previewColorScheme();
      }
    } else {
      analysisContent.slideUp(300);
      $("#toggleAnalysisText").text("Tampilkan Analisis");
      $("#toggleAnalysisBtn").removeClass("btn-primary").addClass("btn-outline-primary");
    }
  }

  /**
   * Update status tombol analisis berdasarkan jumlah warna yang dipilih
   */
  function updateAnalysisControls(enabled) {
    if (previewSchemeBtn.length) {
      previewSchemeBtn.prop("disabled", !enabled);
    }
    if (findSimilarBtn.length) {
      findSimilarBtn.prop("disabled", selectedColorCodes.length === 0);
    }
  }

  /**
   * Preview color scheme analysis
   */
  async function previewColorScheme() {
    if (selectedColorCodes.length < 2) {
      showAnalysisMessage("Pilih minimal 2 warna untuk analisis", "warning");
      return;
    }

    try {
      showAnalysisLoading(true);
      
      const response = await fetch('/api/color-scheme-preview/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
          color_codes: selectedColorCodes
        })
      });

      const data = await response.json();
      
      if (data.success) {
        currentAnalysisData = data;
        displayAnalysisResult(data);
      } else {
        showAnalysisMessage("Error: " + (data.error || "Gagal menganalisis skema warna"), "error");
      }
    } catch (error) {
      console.error("Error previewing color scheme:", error);
      showAnalysisMessage("Gagal terhubung ke server untuk analisis", "error");
    } finally {
      showAnalysisLoading(false);
    }
  }

  /**
   * Find similar colors
   */
  async function findSimilarColors() {
    if (selectedColorCodes.length === 0) {
      showAnalysisMessage("Pilih minimal 1 warna sebagai warna utama", "warning");
      return;
    }

    try {
      showAnalysisLoading(true);
      
      const primaryColor = selectedColorCodes[0];
      const response = await fetch('/api/similar-colors/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
          primary_color: primaryColor,
          count: 5
        })
      });

      const data = await response.json();
      
      if (data.success) {
        // Auto-select similar colors
        data.similar_colors.forEach(colorCode => {
          if (!selectedColorCodes.includes(colorCode)) {
            // Simulasi klik pada color box
            const colorBox = $(`.color-box[data-code="${colorCode}"]`);
            if (colorBox.length) {
              colorBox.click();
            }
          }
        });
        
        showAnalysisMessage(`Ditemukan ${data.similar_colors.length} warna serupa dan ditambahkan ke pilihan`, "success");
        
        // Auto preview setelah menambah warna
        setTimeout(() => {
          if (selectedColorCodes.length >= 2) {
            previewColorScheme();
          }
        }, 500);
      } else {
        showAnalysisMessage("Error: " + (data.error || "Gagal mencari warna serupa"), "error");
      }
    } catch (error) {
      console.error("Error finding similar colors:", error);
      showAnalysisMessage("Gagal terhubung ke server untuk mencari warna serupa", "error");
    } finally {
      showAnalysisLoading(false);
    }
  }

  /**
   * Display analysis result
   */
  function displayAnalysisResult(data) {
    if (!analysisPreview.length) return;

    analysisPreview.html(analysisHTML);
  }

  /**
   * Show analysis loading state
   */
  function showAnalysisLoading(show) {
    if (show) {
      analysisPreview.addClass("loading-analysis");
      previewSchemeBtn.prop("disabled", true);
      findSimilarBtn.prop("disabled", true);
    } else {
      analysisPreview.removeClass("loading-analysis");
      updateAnalysisControls(selectedColorCodes.length >= 2);
    }
  }

  /**
   * Show analysis message
   */
  function showAnalysisMessage(message, type = "info") {
    const typeClass = type === "success" ? "analysis-success" : 
                     type === "warning" ? "analysis-warning" : 
                     type === "error" ? "analysis-error" : "analysis-info";
    
    const messageHTML = `
      <div class="analysis-result ${typeClass} fade-in">
        <div style="padding: 15px; text-align: center;">
          <strong>${message}</strong>
        </div>
      </div>
    `;
    
    analysisPreview.html(messageHTML);
    
    // Auto hide success/warning messages after 3 seconds
    if (type === "success" || type === "warning") {
      setTimeout(() => {
        if (currentAnalysisData) {
          displayAnalysisResult(currentAnalysisData);
        }
      }, 3000);
    }
  }

  /**
   * Display final analysis results
   */
  function displayFinalAnalysis(data) {
    if (!finalColorAnalysis.length) return;

    const analysis = data.color_scheme_analysis || {};
    const scores = data.optimization_scores || {};

    // Update scheme type
    $("#finalSchemeType").text(analysis.scheme_type || 'Unknown');
    $("#finalSchemeDescription").text(analysis.description || 'Tidak ada deskripsi');
  

    // Show final analysis
    finalColorAnalysis.show().addClass("slide-up");
    exportAnalysisBtn.show();
  }

  // =====  FUNGSI UNTUK MENAMPILKAN HASIL KOMBINASI WARNA =====
  function displayColorSchemeResult(data) {
    console.log("displayColorSchemeResult called with data:", data);
    
    if (!data.color_scheme_analysis) {
      console.log("No color_scheme_analysis found in data");
      return;
    }
    
    const analysis = data.color_scheme_analysis;
    console.log("Analysis object:", analysis);
    
    // PERBAIKAN: Gunakan scheme_type bukan best_for
    const schemeType = analysis.scheme_type || 'Tidak diketahui';
    console.log("Scheme type to display:", schemeType);
    
    schemeRecommendation.text(schemeType);
    
    // Tampilkan section hasil
    colorSchemeResult.show();
  }

  /**
   * Export color analysis
   */
  async function exportColorAnalysis() {
    if (!currentTaskId || selectedColorCodes.length === 0) {
      alert("Tidak ada data analisis untuk diekspor");
      return;
    }

    try {
      const url = `/api/export-analysis/?colors=${selectedColorCodes.join(',')}`;
      window.open(url, '_blank');
    } catch (error) {
      console.error("Error exporting analysis:", error);
      alert("Gagal mengekspor analisis");
    }
  }

  /**
   * Get CSRF token
   */
  function getCsrfToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'csrftoken') {
        return value;
      }
    }
    return '';
  }

  /**
   * Handle color selection changes for analysis
   */
  function onColorSelectionChanged() {
    // Show/hide analysis section
    if (selectedColorCodes.length >= 1) {
      colorAnalysisSection.show().addClass("fade-in");
      updateAnalysisControls(selectedColorCodes.length >= 2);
    } else {
      colorAnalysisSection.hide();
      resetAnalysisDisplay();
    }

    // Auto-preview if analysis is visible and enough colors
    if (colorAnalysisVisible && selectedColorCodes.length >= 2) {
      setTimeout(previewColorScheme, 300);
    }
  }

  /**
   * Reset analysis display
   */
  function resetAnalysisDisplay() {
    currentAnalysisData = null;
    if (analysisPreview.length) {
      analysisPreview.html(`
        <div class="empty-state">
          <p>Pilih minimal 2 warna untuk melihat analisis skema warna</p>
        </div>
      `);
    }
    updateAnalysisControls(false);
  }

  // ===== EXPOSE FUNCTIONS TO GLOBAL SCOPE =====
  window.toggleColorAnalysis = toggleColorAnalysis;
  window.previewColorScheme = previewColorScheme;
  window.findSimilarColors = findSimilarColors;
  window.exportColorAnalysis = exportColorAnalysis;

  // ===== END COLOR SCHEME ANALYZER FUNCTIONS =====

  const ulosColorsData = JSON.parse($("#ulosColorsJsonData").val() || "[]");

  $(".color-box").on("click", function () {
    const colorCode = $(this).data("code");
    const index = selectedColorCodes.indexOf(colorCode);

    if (index > -1) {
      selectedColorCodes.splice(index, 1);
      $(this).removeClass("selected");
    } else {
      selectedColorCodes.push(colorCode);
      $(this).addClass("selected");
    }
    updateSelectedColorsDisplay();
    
    // ===== TRIGGER COLOR ANALYSIS UPDATE =====
    onColorSelectionChanged();
  });

  jenisUlosSelect.on("change", async function () {
    const selectedUlosType = $(this).val();

    if (motifCarousel.hasClass("slick-initialized")) {
      motifCarousel.slick("unslick");
    }
    motifCarousel.empty();

    $(".custom-nav-container").remove();

    selectedMotif = "";
    selectedMotifInput.val("");

    if (selectedUlosType) {
      try {
        const response = await fetch(
          `/get_motifs/?jenis_ulos=${selectedUlosType}`
        );
        if (!response.ok) {
          throw new Error("Failed to fetch motif data from server.");
        }
        const motifsData = await response.json();

        if (motifsData.length > 0) {
          motifsData.forEach(function (motif) {
            const slide = $("<div>").addClass("motif-slide");
            const img = $("<img>")
              .attr("src", motif.src)
              .attr("alt", "Motif " + selectedUlosType)
              .attr("data-motif-id", motif.id);
            slide.append(img);
            motifCarousel.append(slide);
          });

          // Buat div container untuk tombol navigasi setelah carousel
          const customNavContainer = $(
            '<div class="custom-nav-container"></div>'
          );
          $(".motif-carousel-wrapper").append(customNavContainer);

          setTimeout(function () {
            motifCarousel.slick({
              dots: true, // Aktifkan dots navigasi
              infinite: true,
              speed: 300,
              slidesToShow: 3,
              slidesToScroll: 1,
              centerMode: true,
              focusOnSelect: true,
              arrows: true,
              appendArrows: $(".custom-nav-container"),
              prevArrow:
                '<button type="button" class="slick-prev">&#9664;</button>',
              nextArrow:
                '<button type="button" class="slick-next">&#9654;</button>',
              customPaging: function (slider, i) {
                // Hanya tampilkan 5 dots di tengah
                const totalSlides = slider.slideCount;
                const middleDot = Math.floor(totalSlides / 2);

                // Logika untuk menampilkan hanya 5 dots di tengah
                if (totalSlides <= 5) {
                  // Jika total slide <= 5, tampilkan semua dots
                  return '<button type="button"></button>';
                } else {
                  // Jika total slide > 5, hanya tampilkan 5 dots di tengah
                  const startDot = Math.max(0, middleDot - 2);
                  const endDot = Math.min(totalSlides - 1, middleDot + 2);

                  if (i >= startDot && i <= endDot) {
                    return '<button type="button"></button>';
                  } else {
                    return ""; // Tidak menampilkan dot ini
                  }
                }
              },
              responsive: [
                {
                  breakpoint: 768,
                  settings: {
                    slidesToShow: 2,
                    slidesToScroll: 1,
                    arrows: true,
                  },
                },
                {
                  breakpoint: 576,
                  settings: {
                    slidesToShow: 1,
                    slidesToScroll: 1,
                    arrows: true,
                  },
                },
              ],
            });

            // Add event handler for slide change
            motifCarousel.on(
              "afterChange",
              function (event, slick, currentSlide) {
                $(".motif-slide").removeClass("selected");
                $(slick.$slides[currentSlide]).addClass("selected");

                // Update selectedMotif
                const img = $(slick.$slides[currentSlide]).find("img");
                if (img.length) {
                  selectedMotif = img.data("motif-id");
                  selectedMotifInput.val(selectedMotif);
                }
              }
            );

            // Force a refresh to ensure proper rendering
            motifCarousel.slick("refresh");

            motifCarouselContainer.show();
            motifCarousel.attr("data-active-ulos", selectedUlosType);

            const firstMotif = motifsData[0];
            selectedMotif = firstMotif.id;
            selectedMotifInput.val(selectedMotif);

            // Select first slide after a short delay to ensure proper initialization
            setTimeout(function () {
              motifCarousel.find(".slick-slide:first").addClass("selected");
            }, 100);
          }, 50);
        } else {
          motifCarouselContainer.hide();
          errorMessage.text(
            "Tidak ada motif yang tersedia untuk jenis Ulos ini."
          );
        }
      } catch (error) {
        console.error("Error fetching motifs:", error);
        errorMessage.text("Failed to load motifs. Please try again.");
        motifCarouselContainer.hide();
      }
    } else {
      motifCarouselContainer.hide();
    }
  });

  $(document).on("click", ".motif-slide", function (e) {
    e.preventDefault();

    $(".motif-slide").removeClass("selected");
    $(this).addClass("selected");

    const img = $(this).find("img");
    if (img.length) {
      selectedMotif = img.data("motif-id");
      selectedMotifInput.val(selectedMotif);
    }

    errorMessage.text("");
  });

  function updateSelectedColorsDisplay() {
    selectedColorsContainer.empty();
    selectedColorCodes.forEach(function (code) {
      const colorObj = ulosColorsData.find((color) => color.code === code);
      if (colorObj) {
        const colorContainer = $("<div>").addClass("selected-color-container");
        const codeLabel = $("<div>").addClass("selected-color-name").text(code);
        const colorDiv = $("<div>")
          .addClass("selected-color-box")
          .attr("data-code", code)
          .css("background-color", colorObj.hex_color);
        const removeBtn = $("<span>")
          .addClass("remove-color-btn")
          .html("&times;")
          .attr("data-code", colorObj.code);

        colorContainer.append(codeLabel);
        colorContainer.append(colorDiv);
        colorDiv.append(removeBtn);
        selectedColorsContainer.append(colorContainer);
      }
    });
    colorCounter.text(`${selectedColorCodes.length} warna dipilih`);
    selectedColorsInput.val(selectedColorCodes.join(","));
  }

  if (selectedColorsInput.val()) {
    selectedColorCodes = selectedColorsInput.val().split(",").filter(Boolean);
    selectedColorCodes.forEach((code) => {
      $(`.color-box[data-code="${code}"]`).addClass("selected");
    });
    updateSelectedColorsDisplay();
    
    // ===== TRIGGER INITIAL COLOR ANALYSIS UPDATE =====
    onColorSelectionChanged();
  }

  $(document).on("click", ".remove-color-btn", function () {
    const colorCodeToRemove = $(this).attr("data-code");
    selectedColorCodes = selectedColorCodes.filter(
      (code) => code !== colorCodeToRemove
    );
    $(`.color-box[data-code="${colorCodeToRemove}"]`).removeClass("selected");
    updateSelectedColorsDisplay();
    
    // ===== TRIGGER COLOR ANALYSIS UPDATE =====
    onColorSelectionChanged();
  });

  // ===== MODIFIKASI: Handler submit form untuk menampilkan LOADING SPINNER + LOADING BAR + ANALISIS =====
  coloringForm.on("submit", async function (e) {
    e.preventDefault();

    // Reset UI
    errorMessage.text("");
    coloredImage.hide();
    noImageMessage.show();
    downloadImageBtn.hide();
    downloadPdfBtn.hide();
    exportAnalysisBtn.hide();
    usedColorsDisplay.hide();
    finalColorAnalysis.hide();
    colorSchemeResult.hide(); // ===== RESET COLOR SCHEME RESULT =====
    actualUsedColorsPalette.empty();

    // Validasi input di frontend
    const jenisUlos = $("#jenisUlos").val();
    const colorCount = selectedColorCodes.length;
    
    if (!jenisUlos && colorCount < 2) {
      errorMessage.text("Harap pilih Jenis Ulos dan minimal 2 warna benang.");
      return;
    }
    
    if (!jenisUlos) {
      errorMessage.text("Harap pilih Jenis Ulos.");
      return;
    }
    
    if (colorCount < 2) {
      errorMessage.text("Harap pilih minimal 2 warna benang.");
      return;
}

    // Tampilkan UI loading
    loadingSpinner.show();
    loadingBarContainer.show();
    progressSection.show(); // ===== TAMPILKAN PROGRESS SECTION BARU =====
    updateLoadingBar(0);
    updateColorAnalysisProgress(0); // ===== UPDATE PROGRESS ANALYZER =====
    submitButton.prop("disabled", true);

    const formData = new FormData(this);
    let pollInterval;
    currentTaskId = null;

    // Fungsi untuk menghentikan semua proses loading di UI
    function stopLoading() {
      if (pollInterval) clearInterval(pollInterval);
      loadingSpinner.hide();
      setTimeout(() => {
        loadingBarContainer.hide();
        progressSection.hide(); // ===== SEMBUNYIKAN PROGRESS SECTION =====
        updateLoadingBar(0); // Reset bar untuk proses selanjutnya
        updateColorAnalysisProgress(0); // ===== RESET PROGRESS ANALYZER =====
      }, 1500); // Beri jeda 1.5 detik agar user bisa lihat 100%
      submitButton.prop("disabled", false);
    }

    // Fungsi untuk polling progres ke server
    function pollProgress(taskId) {
      currentTaskId = taskId; // ===== SIMPAN TASK ID =====
      
      pollInterval = setInterval(async () => {
        try {
          // Tanya ke server "bagaimana progres task ini?"
          const response = await fetch(`/pewarnaan/progress/${taskId}/`);
          if (!response.ok) {
            throw new Error(
              `Polling failed: Server responded with status ${response.status}`
            );
          }
          const data = await response.json();

          // Update loading bar sesuai data dari server
          updateLoadingBar(data.progress || 0);
          updateColorAnalysisProgress(data.progress || 0); // ===== UPDATE PROGRESS ANALYZER =====

          // Cek jika proses sudah 100% (selesai atau error)
          if (data.progress >= 100) {
            clearInterval(pollInterval); // Hentikan polling

            if (data.status === "Completed") {
              // Jika sukses, tampilkan semua hasilnya
              const imageUrl = "/static/" + data.colored_image_url;
              coloredImage.attr("src", imageUrl).show();
              noImageMessage.hide();
              downloadImageBtn.attr("href", imageUrl);
              downloadImageBtn.show();
              downloadPdfBtn.show();

              // ===== TAMPILKAN HASIL ANALISIS WARNA =====
              if (data.color_scheme_analysis) {
                displayFinalAnalysis(data);
                
                // ===== TAMBAHAN: TAMPILKAN HASIL KOMBINASI WARNA SEDERHANA =====
                displayColorSchemeResult(data);
              }

              // Display used colors
              if (data.used_colors && data.used_colors.length > 0) {
                actualUsedColorsPalette.empty();
                data.used_colors.forEach(function (color) {
                  const colorItem = $("<div>")
                    .addClass("used-color-item")
                    .attr("title", `Code: ${color.code}`);
                  const colorBox = $("<div>")
                    .addClass("used-color-box")
                    .css("background-color", color.hex_color);
                  const colorCodeLabel = $("<div>")
                    .addClass("used-color-code")
                    .text(color.code);
                  colorItem.append(colorBox).append(colorCodeLabel);
                  actualUsedColorsPalette.append(colorItem);
                });
                usedColorsDisplay.show();
              }
            } else {
              // Jika selesai dengan error, tampilkan pesan error
              errorMessage.text(
                `Error: ${data.error || "Terjadi kesalahan tidak diketahui."}`
              );
            }

            // Apapun hasilnya (sukses/error), hentikan UI loading
            stopLoading();
          }
        } catch (error) {
          console.error("Polling error:", error);
          errorMessage.text(
            "Gagal terhubung ke server untuk update progres. Coba lagi."
          );
          stopLoading();
        }
      }, 500);
    }

    // === Langkah Utama saat tombol disubmit ===
    try {
      // 1. Kirim request untuk MEMULAI proses pewarnaan
      const initialResponse = await fetch("/pewarnaan/", {
        method: "POST",
        body: formData,
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      if (!initialResponse.ok) {
        const errorData = await initialResponse.json();
        throw new Error(
          errorData.error || "Gagal memulai proses pewarnaan di server."
        );
      }

      const initialData = await initialResponse.json();

      // 2. Jika server merespon dengan task_id, mulai polling
      if (initialData.task_id) {
        pollProgress(initialData.task_id);
      } else {
        throw new Error(
          "Server tidak memberikan Task ID. Proses tidak bisa dilanjutkan."
        );
      }
    } catch (error) {
      console.error("Submission error:", error);
      errorMessage.text(error.message);
      stopLoading();
    }
  });

  // ===== INITIALIZE COLOR ANALYSIS ON PAGE LOAD =====
  setTimeout(() => {
    onColorSelectionChanged();
  }, 500);
});