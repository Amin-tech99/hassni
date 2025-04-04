document.addEventListener('DOMContentLoaded', () => {
    console.log("Admin page initialized");
    
    // File upload preview
    const fileInput = document.getElementById('audio_file');
    const fileLabel = document.querySelector('.custom-file-label');
    const uploadForm = document.getElementById('upload-form');
    
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            const fileName = e.target.files[0]?.name || 'Choose file';
            if (fileLabel) {
                fileLabel.textContent = fileName;
            }
        });
    }
    
    if (uploadForm) {
        uploadForm.addEventListener('submit', (e) => {
            const submitBtn = uploadForm.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Uploading & Processing...';
            }
        });
    }
    
    // Clip assignment checkboxes
    const clipCheckboxes = document.querySelectorAll('.clip-checkbox');
    const selectAllCheckbox = document.getElementById('select-all-clips');
    const selectedCountSpan = document.getElementById('selected-count');
    
    if (clipCheckboxes.length > 0 && selectAllCheckbox) {
        // Select all functionality
        selectAllCheckbox.addEventListener('change', () => {
            const isChecked = selectAllCheckbox.checked;
            clipCheckboxes.forEach(checkbox => {
                checkbox.checked = isChecked;
            });
            updateSelectedCount();
        });
        
        // Individual checkbox change
        clipCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                updateSelectedCount();
                
                // Update "select all" if all individual checkboxes are checked/unchecked
                const allChecked = Array.from(clipCheckboxes).every(cb => cb.checked);
                const allUnchecked = Array.from(clipCheckboxes).every(cb => !cb.checked);
                
                if (allChecked) {
                    selectAllCheckbox.checked = true;
                    selectAllCheckbox.indeterminate = false;
                } else if (allUnchecked) {
                    selectAllCheckbox.checked = false;
                    selectAllCheckbox.indeterminate = false;
                } else {
                    selectAllCheckbox.indeterminate = true;
                }
            });
        });
        
        function updateSelectedCount() {
            if (selectedCountSpan) {
                const checkedCount = Array.from(clipCheckboxes).filter(cb => cb.checked).length;
                selectedCountSpan.textContent = checkedCount;
                
                // Enable/disable assign button
                const assignButton = document.querySelector('.assign-btn');
                if (assignButton) {
                    assignButton.disabled = checkedCount === 0;
                }
            }
        }
        
        // Initialize count
        updateSelectedCount();
    }
    
    // Review transcriptions
    const approveButtons = document.querySelectorAll('.approve-btn');
    const rejectButtons = document.querySelectorAll('.reject-btn');
    const editButtons = document.querySelectorAll('.edit-btn');
    
    approveButtons.forEach(button => {
        button.addEventListener('click', function() {
            const transcriptionId = this.getAttribute('data-transcription-id');
            const cardElement = document.getElementById(`card-${transcriptionId}`);
            const textInput = document.getElementById(`text-${transcriptionId}`);
            
            // Disable buttons during processing
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
            
            const formData = new FormData();
            if (textInput) {
                formData.append('text', textInput.value);
            }
            
            fetch(`/admin/approve_transcription/${transcriptionId}`, {
                method: 'POST',
                body: formData,
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update UI to show approved state
                    if (cardElement) {
                        cardElement.classList.remove('border-warning');
                        cardElement.classList.add('border-success');
                        
                        const statusBadge = cardElement.querySelector('.status-badge');
                        if (statusBadge) {
                            statusBadge.textContent = 'Approved';
                            statusBadge.classList.remove('bg-warning');
                            statusBadge.classList.add('bg-success');
                        }
                        
                        // Disable all buttons for this transcription
                        const allButtons = cardElement.querySelectorAll('button');
                        allButtons.forEach(btn => {
                            btn.disabled = true;
                        });
                        
                        // Re-enable only the edit button
                        const editBtn = cardElement.querySelector('.edit-btn');
                        if (editBtn) {
                            editBtn.disabled = false;
                        }
                    }
                } else {
                    alert('Error approving transcription');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Network error occurred');
            })
            .finally(() => {
                // Reset button
                this.disabled = false;
                this.textContent = 'Approve';
            });
        });
    });
    
    rejectButtons.forEach(button => {
        button.addEventListener('click', function() {
            const transcriptionId = this.getAttribute('data-transcription-id');
            const cardElement = document.getElementById(`card-${transcriptionId}`);
            
            // Confirm rejection
            if (!confirm('Are you sure you want to reject this transcription? It will be sent back to the transcriber.')) {
                return;
            }
            
            // Disable buttons during processing
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
            
            fetch(`/admin/reject_transcription/${transcriptionId}`, {
                method: 'POST',
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update UI to show rejected state
                    if (cardElement) {
                        cardElement.classList.remove('border-warning');
                        cardElement.classList.add('border-danger');
                        
                        const statusBadge = cardElement.querySelector('.status-badge');
                        if (statusBadge) {
                            statusBadge.textContent = 'Rejected';
                            statusBadge.classList.remove('bg-warning');
                            statusBadge.classList.add('bg-danger');
                        }
                        
                        // Hide the card after a delay
                        setTimeout(() => {
                            cardElement.style.display = 'none';
                        }, 2000);
                    }
                } else {
                    alert('Error rejecting transcription');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Network error occurred');
            })
            .finally(() => {
                // Reset button
                this.disabled = false;
                this.textContent = 'Reject';
            });
        });
    });
    
    editButtons.forEach(button => {
        button.addEventListener('click', function() {
            const transcriptionId = this.getAttribute('data-transcription-id');
            const textInput = document.getElementById(`text-${transcriptionId}`);
            
            if (textInput) {
                // Toggle readonly
                const isEditing = textInput.readOnly;
                textInput.readOnly = !isEditing;
                
                if (isEditing) {
                    // Entering edit mode
                    this.textContent = 'Save';
                    textInput.classList.add('border', 'border-primary');
                    textInput.focus();
                } else {
                    // Saving changes
                    this.textContent = 'Edit';
                    textInput.classList.remove('border', 'border-primary');
                    
                    // Save the changes if already approved
                    const cardElement = document.getElementById(`card-${transcriptionId}`);
                    const statusBadge = cardElement?.querySelector('.status-badge');
                    
                    if (statusBadge && statusBadge.textContent === 'Approved') {
                        // Send changes to server
                        const formData = new FormData();
                        formData.append('text', textInput.value);
                        
                        fetch(`/admin/approve_transcription/${transcriptionId}`, {
                            method: 'POST',
                            body: formData,
                            credentials: 'same-origin'
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (!data.success) {
                                alert('Error saving changes');
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            alert('Network error occurred');
                        });
                    }
                }
            }
        });
    });
    
    // Delete audio confirmation
    const deleteButtons = document.querySelectorAll('.delete-audio-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this audio file and all associated clips? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });
    
    // Audio player in review page
    const reviewAudioPlayers = document.querySelectorAll('.review-audio-player');
    console.log(`Found ${reviewAudioPlayers.length} review audio players`);
    
    reviewAudioPlayers.forEach(player => {
        // Add event listeners for audio player events
        player.addEventListener('error', (e) => {
            console.error("Audio player error:", e);
        });
        
        player.addEventListener('loadeddata', () => {
            console.log("Review audio loaded successfully");
        });
        
        const speedButtons = player.parentElement.querySelectorAll('.speed-btn');
        console.log(`Found ${speedButtons.length} speed buttons for player`);
        
        speedButtons.forEach(button => {
            button.addEventListener('click', () => {
                const speed = parseFloat(button.getAttribute('data-speed'));
                console.log(`Setting playback speed to ${speed}`);
                player.playbackRate = speed;
                
                // Update active button within this container
                const container = button.closest('.speed-controls');
                if (container) {
                    container.querySelectorAll('.speed-btn').forEach(btn => {
                        btn.classList.remove('btn-primary');
                        btn.classList.add('btn-outline-primary');
                    });
                    button.classList.remove('btn-outline-primary');
                    button.classList.add('btn-primary');
                }
            });
        });
    });
    
    // Check all audio source URLs
    const allAudioPlayers = document.querySelectorAll('audio');
    console.log(`Found ${allAudioPlayers.length} total audio players on the page`);
    
    allAudioPlayers.forEach((player, index) => {
        console.log(`Audio player ${index+1} source: ${player.src}`);
    });
});
