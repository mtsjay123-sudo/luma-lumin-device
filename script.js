document.addEventListener('DOMContentLoaded', () => {
    // Animation Sequence
    // Headline: delay 60ms
    // Label: delay 100ms
    // Body: delay 140ms
    // CTA: delay 160ms

    setTimeout(() => {
        const headline = document.querySelector('.headline');
        if (headline) headline.classList.add('visible');
    }, 60);

    setTimeout(() => {
        const label = document.querySelector('.label');
        if (label) label.classList.add('visible');
    }, 100);

    setTimeout(() => {
        const body = document.querySelector('.body-copy');
        if (body) body.classList.add('visible');
    }, 140);

    setTimeout(() => {
        const bottomBar = document.querySelector('.bottom-bar');
        if (bottomBar) bottomBar.classList.add('visible');
    }, 160);

    // Button interactions
    const buttons = document.querySelectorAll('.pill-btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            console.log(`Button clicked: ${e.target.innerText}`);
            // Visual feedback handled by CSS :active, but could add ripple here if needed
        });
    });



    const backBtn = document.querySelector('.back-button');
    if (backBtn) {
        backBtn.addEventListener('click', () => {
            console.log('Back button clicked');
            window.location.href = 'index.html';
        });
    }

    // Reservation Logic
    const reserveBtn = document.getElementById('reserveBtn');
    const modal = document.getElementById('reservationModal');
    const closeModal = document.getElementById('closeModal');
    const closeSuccessModal = document.getElementById('closeSuccessModal');
    const reservationForm = document.getElementById('reservationForm');

    const formView = document.getElementById('modalFormView');
    const successView = document.getElementById('modalSuccessView');

    if (reserveBtn && modal && closeModal) {
        // Open Modal
        reserveBtn.addEventListener('click', () => {
            // Reset state when opening
            if (formView && successView) {
                formView.style.display = 'block';
                successView.style.display = 'none';
            }
            modal.classList.add('active');
        });

        // Close Modal
        closeModal.addEventListener('click', () => {
            modal.classList.remove('active');
        });

        // Close Success Modal
        if (closeSuccessModal) {
            closeSuccessModal.addEventListener('click', () => {
                modal.classList.remove('active');
            });
        }

        // Close on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });

        // Handle Form Submission
        if (reservationForm) {
            reservationForm.addEventListener('submit', async (e) => {
                e.preventDefault();

                const email = document.getElementById('resEmail').value;
                const phone = document.getElementById('resPhone').value;
                const timestamp = new Date().toISOString();

                const newEntry = { email, phone, timestamp };

                try {
                    const response = await fetch('/api/reserve', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(newEntry)
                    });

                    if (response.ok) {
                        // Switch to Success View
                        if (formView && successView) {
                            formView.style.display = 'none';
                            successView.style.display = 'flex';
                        }

                        // Reset Form
                        reservationForm.reset();
                        console.log('Saved to server:', newEntry);
                    } else {
                        alert('Something went wrong. Please try again.');
                        console.error('Server error:', await response.text());
                    }
                } catch (err) {
                    console.error('Network error:', err);
                    alert('Could not connect to the server.');
                }
            });
        }
    }
});
