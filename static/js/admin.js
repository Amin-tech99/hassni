document.addEventListener('DOMContentLoaded', () => {
    console.log("Admin page initialized");
    
    // Detect mobile device
    const isMobile = window.innerWidth < 768;
    
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
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Uploading...';
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
                this.innerHTML = isMobile ? '<i class="fas fa-check"></i>' : 'Approve';
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
                this.innerHTML = isMobile ? '<i class="fas fa-times"></i>' : 'Reject';
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
                    this.innerHTML = isMobile ? '<i class="fas fa-save"></i>' : 'Save';
                    textInput.classList.add('border', 'border-primary');
                    textInput.focus();
                } else {
                    // Saving changes
                    this.innerHTML = isMobile ? '<i class="fas fa-edit"></i>' : 'Edit';
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
    const deleteButtons = document.querySelectorAll('.delete-audio');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function() {
            const audioId = this.getAttribute('data-audio-id');
            const audioName = this.getAttribute('data-audio-name');
            
            if (confirm(`Are you sure you want to delete "${audioName}"? This action cannot be undone and will delete all associated clips and transcriptions.`)) {
                window.location.href = `/admin/delete_audio/${audioId}`;
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
        
        // For mobile optimization
        if (isMobile) {
            // Make audio controls more touch-friendly
            player.style.height = "40px";
        }
        
        // Add custom speed controls if needed
        const parentRow = player.closest('tr');
        if (parentRow) {
            // You could add custom playback speed controls here if needed
        }
    });
    
    // Mobile specific optimizations
    if (isMobile) {
        // Make table cells more readable on mobile
        const tableCells = document.querySelectorAll('td, th');
        tableCells.forEach(cell => {
            if (cell.classList.contains('text-center')) {
                cell.style.padding = "0.5rem";
            }
        });
        
        // Enhance button touch targets
        const allButtons = document.querySelectorAll('.btn-sm');
        allButtons.forEach(btn => {
            btn.classList.add('mb-1', 'me-1');
            btn.style.minWidth = "36px";
            btn.style.minHeight = "36px";
        });
        
        // Add scroll indicator for tables
        const allTables = document.querySelectorAll('.table-responsive');
        allTables.forEach(tableContainer => {
            if (tableContainer.scrollWidth > tableContainer.clientWidth) {
                // Add indicator that table is scrollable
                const indicator = document.createElement('div');
                indicator.className = 'text-center text-muted small mt-2';
                indicator.textContent = 'Swipe to see more →';
                tableContainer.parentNode.insertBefore(indicator, tableContainer.nextSibling);
            }
        });
    }
    
    // Check all audio source URLs
    const allAudioPlayers = document.querySelectorAll('audio');
    console.log(`Found ${allAudioPlayers.length} total audio players on the page`);
});
