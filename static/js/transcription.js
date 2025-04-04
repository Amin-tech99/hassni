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
            });
        });
        
        // Trigger click on first clip to load it
        console.log("Clicking first clip to load it");
        clipItems[0].click();
    } else {
        console.warn("No clip items found - audio player won't be initialized");
    }
});
