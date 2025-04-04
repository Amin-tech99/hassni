document.addEventListener('DOMContentLoaded', () => {
    // Audio player and speed controls
    const audioPlayer = document.getElementById('audio-player');
    if (audioPlayer) {
        const speedButtons = document.querySelectorAll('.speed-btn');
        
        // Set up speed control buttons
        speedButtons.forEach(button => {
            button.addEventListener('click', () => {
                const speed = parseFloat(button.getAttribute('data-speed'));
                audioPlayer.playbackRate = speed;
                
                // Update active button
                speedButtons.forEach(btn => btn.classList.remove('btn-primary'));
                speedButtons.forEach(btn => btn.classList.add('btn-outline-primary'));
                button.classList.remove('btn-outline-primary');
                button.classList.add('btn-primary');
            });
        });
        
        // Set default speed to 1x
        audioPlayer.playbackRate = 1.0;
    }
    
    // Clip selection in sidebar
    const clipItems = document.querySelectorAll('.clip-item');
    if (clipItems.length > 0) {
        clipItems.forEach(item => {
            item.addEventListener('click', function() {
                const clipId = this.getAttribute('data-clip-id');
                const clipUrl = this.getAttribute('data-clip-url');
                const clipStatus = this.getAttribute('data-clip-status');
                
                // Update active clip
                clipItems.forEach(ci => ci.classList.remove('active'));
                this.classList.add('active');
                
                // Load clip in audio player
                if (audioPlayer) {
                    audioPlayer.src = clipUrl;
                    audioPlayer.load();
                }
                
                // Set the clip ID in the form
                const clipIdInput = document.getElementById('clip_id');
                if (clipIdInput) {
                    clipIdInput.value = clipId;
                }
                
                // Load existing transcription if any
                const transcriptionText = document.getElementById('transcription-text-' + clipId);
                const transcriptionInput = document.getElementById('text');
                if (transcriptionText && transcriptionInput) {
                    transcriptionInput.value = transcriptionText.value;
                } else {
                    if (transcriptionInput) {
                        transcriptionInput.value = '';
                    }
                }
                
                // Show this clip's transcription form
                const transcriptionForms = document.querySelectorAll('.transcription-form');
                transcriptionForms.forEach(form => {
                    form.style.display = 'none';
                });
                
                const currentForm = document.getElementById('transcription-form-' + clipId);
                if (currentForm) {
                    currentForm.style.display = 'block';
                }
                
                // Enable/disable submit button based on status
                const submitBtn = document.querySelector('.submit-btn');
                const saveBtn = document.querySelector('.save-btn');
                if (submitBtn && saveBtn) {
                    if (clipStatus === 'submitted' || clipStatus === 'completed') {
                        submitBtn.disabled = true;
                        saveBtn.disabled = true;
                    } else {
                        submitBtn.disabled = false;
                        saveBtn.disabled = false;
                    }
                }
            });
        });
        
        // Trigger click on first clip to load it
        if (clipItems.length > 0) {
            clipItems[0].click();
        }
    }
    
    // Handle form submission via AJAX
    const transcriptionForm = document.getElementById('transcription-form');
    if (transcriptionForm) {
        const saveBtn = document.querySelector('.save-btn');
        const submitBtn = document.querySelector('.submit-btn');
        const submitTypeInput = document.getElementById('submit_type');
        
        if (saveBtn) {
            saveBtn.addEventListener('click', function(e) {
                e.preventDefault();
                submitTypeInput.value = 'save';
                saveTranscription();
            });
        }
        
        if (submitBtn) {
            submitBtn.addEventListener('click', function(e) {
                e.preventDefault();
                submitTypeInput.value = 'submit';
                saveTranscription();
            });
        }
        
        function saveTranscription() {
            const formData = new FormData(transcriptionForm);
            
            // Display loading state
            const submitButtons = transcriptionForm.querySelectorAll('button[type="submit"]');
            submitButtons.forEach(btn => {
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
            });
            
            fetch('/transcriber/save_transcription', {
                method: 'POST',
                body: formData,
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show success message
                    const alertDiv = document.createElement('div');
                    alertDiv.className = 'alert alert-success alert-dismissible fade show mt-3';
                    alertDiv.role = 'alert';
                    alertDiv.innerHTML = `
                        ${data.message}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    `;
                    transcriptionForm.appendChild(alertDiv);
                    
                    // Update clip status in UI
                    const activeClip = document.querySelector('.clip-item.active');
                    if (activeClip) {
                        const clipId = activeClip.getAttribute('data-clip-id');
                        const statusType = submitTypeInput.value === 'submit' ? 'submitted' : 'assigned';
                        
                        // Update status badge
                        const statusBadge = activeClip.querySelector('.badge');
                        if (statusBadge) {
                            statusBadge.textContent = statusType === 'submitted' ? 'Submitted' : 'In Progress';
                            statusBadge.className = statusType === 'submitted' 
                                ? 'badge bg-success status-badge'
                                : 'badge bg-primary status-badge';
                        }
                        
                        // Update data attribute
                        activeClip.setAttribute('data-clip-status', statusType);
                        
                        // If submitted, disable buttons
                        if (statusType === 'submitted') {
                            submitButtons.forEach(btn => {
                                btn.disabled = true;
                            });
                        }
                        
                        // Update hidden field with current text
                        const hiddenTranscription = document.getElementById('transcription-text-' + clipId);
                        if (hiddenTranscription) {
                            const textInput = document.getElementById('text');
                            hiddenTranscription.value = textInput.value;
                        }
                    }
                    
                    // Auto-dismiss the alert after 3 seconds
                    setTimeout(() => {
                        const alert = document.querySelector('.alert');
                        if (alert) {
                            const bsAlert = new bootstrap.Alert(alert);
                            bsAlert.close();
                        }
                    }, 3000);
                } else {
                    // Show error message
                    const alertDiv = document.createElement('div');
                    alertDiv.className = 'alert alert-danger alert-dismissible fade show mt-3';
                    alertDiv.role = 'alert';
                    alertDiv.innerHTML = `
                        Error: ${data.error || 'Something went wrong'}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    `;
                    transcriptionForm.appendChild(alertDiv);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                // Show error message
                const alertDiv = document.createElement('div');
                alertDiv.className = 'alert alert-danger alert-dismissible fade show mt-3';
                alertDiv.role = 'alert';
                alertDiv.innerHTML = `
                    Error: ${error.message || 'Network error occurred'}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                `;
                transcriptionForm.appendChild(alertDiv);
            })
            .finally(() => {
                // Reset button states
                submitButtons.forEach(btn => {
                    btn.disabled = false;
                    if (btn.classList.contains('save-btn')) {
                        btn.innerHTML = 'Save Draft';
                    } else {
                        btn.innerHTML = 'Submit';
                    }
                });
            });
        }
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Only apply when not typing in a text field
        if (e.target.tagName !== 'TEXTAREA' && e.target.tagName !== 'INPUT') {
            // Space to play/pause
            if (e.code === 'Space' && audioPlayer) {
                e.preventDefault();
                if (audioPlayer.paused) {
                    audioPlayer.play();
                } else {
                    audioPlayer.pause();
                }
            }
            
            // Number keys 1-3 for speed control
            if (e.code === 'Digit1' || e.code === 'Numpad1') {
                e.preventDefault();
                if (audioPlayer) audioPlayer.playbackRate = 0.5;
                updateSpeedButton(0.5);
            }
            if (e.code === 'Digit2' || e.code === 'Numpad2') {
                e.preventDefault();
                if (audioPlayer) audioPlayer.playbackRate = 1.0;
                updateSpeedButton(1.0);
            }
            if (e.code === 'Digit3' || e.code === 'Numpad3') {
                e.preventDefault();
                if (audioPlayer) audioPlayer.playbackRate = 1.5;
                updateSpeedButton(1.5);
            }
        }
    });
    
    function updateSpeedButton(speed) {
        const speedButtons = document.querySelectorAll('.speed-btn');
        speedButtons.forEach(btn => {
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-outline-primary');
            if (parseFloat(btn.getAttribute('data-speed')) === speed) {
                btn.classList.remove('btn-outline-primary');
                btn.classList.add('btn-primary');
            }
        });
    }
});
