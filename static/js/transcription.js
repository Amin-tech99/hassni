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
    }
    
    // Handle transcription form submission
    const transcriptionForm = document.getElementById("transcription-form");
    const submitTypeInput = document.getElementById("submit_type");
    
    if (transcriptionForm && submitTypeInput) {
        transcriptionForm.addEventListener("submit", function(e) {
            // Set the submit_type to 'save' by default when the form is submitted
            submitTypeInput.value = 'save';
            console.log("Form submitted with submit_type:", submitTypeInput.value);
        });
        
        // Add submit button for saving and submitting
        const saveButton = transcriptionForm.querySelector("button[type='submit']");
        const submitButton = document.createElement("button");
        submitButton.type = "button";
        submitButton.className = "btn btn-success ms-2";
        submitButton.textContent = "Submit";
        submitButton.addEventListener("click", function() {
            submitTypeInput.value = 'submit';
            console.log("Setting submit_type to:", submitTypeInput.value);
            transcriptionForm.submit();
        });
        
        if (saveButton) {
            saveButton.parentNode.insertBefore(submitButton, saveButton.nextSibling);
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
                }
            });
        });
        
        // Trigger click on first clip to load it
        console.log("Clicking first clip to load it");
        clipItems[0].click();
    } else {
        console.warn("No clip items found - audio player won't be initialized");
    }
});
