document.addEventListener("DOMContentLoaded", () => {
    console.log("Transcription page initialized");
    
    // Audio player setup
    const audioPlayer = document.getElementById("audio-player");
    if (!audioPlayer) {
        console.error("Audio player element not found");
    } else {
        console.log("Audio player element found");
        
        // Add event listeners for audio player events
        audioPlayer.addEventListener('error', (e) => {
            console.error("Audio player error:", e);
        });
        
        audioPlayer.addEventListener('loadeddata', () => {
            console.log("Audio loaded successfully");
        });
        
        // Add playback control buttons functionality
        const halfSpeedBtn = document.getElementById("play-half-speed");
        const normalSpeedBtn = document.getElementById("play-normal-speed");
        const repeatBtn = document.getElementById("repeat-audio");
        
        if (halfSpeedBtn) {
            halfSpeedBtn.addEventListener("click", () => {
                audioPlayer.playbackRate = 0.5;
                if (audioPlayer.paused) audioPlayer.play();
            });
        }
        
        if (normalSpeedBtn) {
            normalSpeedBtn.addEventListener("click", () => {
                audioPlayer.playbackRate = 1.0;
                if (audioPlayer.paused) audioPlayer.play();
            });
        }
        
        if (repeatBtn) {
            repeatBtn.addEventListener("click", () => {
                audioPlayer.currentTime = 0;
                audioPlayer.play();
            });
        }
    }
    
    // Handle transcription form submission
    const transcriptionForm = document.getElementById("transcription-form");
    const submitTypeInput = document.getElementById("submit_type");
    const saveBtn = document.getElementById("save-btn");
    const submitBtn = document.getElementById("submit-btn");
    
    if (transcriptionForm && submitTypeInput) {
        if (saveBtn) {
            saveBtn.addEventListener("click", function() {
                submitTypeInput.value = 'save';
                console.log("Setting submit_type to 'save'");
                transcriptionForm.submit();
            });
        }
        
        if (submitBtn) {
            submitBtn.addEventListener("click", function() {
                submitTypeInput.value = 'submit';
                console.log("Setting submit_type to 'submit'");
                transcriptionForm.submit();
            });
        }
    }
    
    // Clip selection in sidebar
    const clipItems = document.querySelectorAll(".clip-item");
    console.log(`Found ${clipItems.length} clip items`);
    
    if (clipItems.length > 0) {
        clipItems.forEach(item => {
            item.addEventListener("click", function() {
                const clipId = this.getAttribute("data-clip-id");
                const clipUrl = this.getAttribute("data-clip-url");
                
                console.log(`Clicked clip: ${clipId}, URL: ${clipUrl}`);
                
                // Update active clip
                clipItems.forEach(ci => ci.classList.remove("active"));
                this.classList.add("active");
                
                // Load clip in audio player
                if (audioPlayer) {
                    console.log(`Setting audio source to: ${clipUrl}`);
                    audioPlayer.src = clipUrl;
                    audioPlayer.load();
                }
                
                // Set the clip ID in the form
                const clipIdInput = document.getElementById("clip_id");
                if (clipIdInput) {
                    clipIdInput.value = clipId;
                    console.log(`Set clip ID in form: ${clipId}`);
                } else {
                    console.warn("Clip ID input not found in form");
                }
                
                // Load existing transcription if available
                const clipStatus = this.getAttribute("data-clip-status");
                const textArea = document.getElementById("text");
                
                if (textArea) {
                    // Use AJAX to fetch transcription text if needed
                    // For now, we're assuming the transcription is loaded with the page
                    console.log(`Clip status: ${clipStatus}`);
                    
                    // On mobile, scroll to the transcription area after selecting a clip
                    if (window.innerWidth < 768) {
                        const transcriptionCard = document.querySelector(".col-md-8 .card");
                        if (transcriptionCard) {
                            setTimeout(() => {
                                transcriptionCard.scrollIntoView({ behavior: 'smooth' });
                            }, 300);
                        }
                    }
                }
            });
        });
        
        // Trigger click on first clip to load it
        console.log("Clicking first clip to load it");
        clipItems[0].click();
    } else {
        console.warn("No clip items found - audio player won't be initialized");
    }
    
    // Add touch-friendly features for mobile
    if (window.innerWidth < 768) {
        // Make clip items slightly larger for touch targets
        clipItems.forEach(item => {
            item.style.padding = "15px";
        });
        
        // Auto-expand textarea when focused on mobile
        const textarea = document.getElementById("text");
        if (textarea) {
            textarea.addEventListener("focus", function() {
                this.rows = 6;
            });
            
            textarea.addEventListener("blur", function() {
                this.rows = 4;
            });
        }
    }
});
