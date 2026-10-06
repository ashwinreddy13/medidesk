document.addEventListener('DOMContentLoaded', () => {
  // 1. Dynamic Slot Fetcher for Appointment Booking
  const doctorSelect = document.getElementById('doctorSelect');
  const dateInput = document.getElementById('appointmentDate');
  const slotContainer = document.getElementById('slotContainer');
  const timeHiddenInput = document.getElementById('selectedTime');
  const slotStatusMsg = document.getElementById('slotStatusMsg');

  function fetchSlots() {
    if (!doctorSelect || !dateInput || !slotContainer) return;

    const doctorId = doctorSelect.value;
    const dateVal = dateInput.value;

    if (!doctorId || !dateVal) {
      slotContainer.innerHTML = '<p class="text-muted" style="color: #64748B; font-size: 0.875rem;">Please select both a doctor and date to view available appointment slots.</p>';
      return;
    }

    slotContainer.innerHTML = '<p style="color: #2563EB; font-size: 0.875rem;">Checking doctor schedule and available slots...</p>';
    const prevTime = timeHiddenInput ? timeHiddenInput.value : '';

    fetch(`/patient/api/slots?doctor_id=${encodeURIComponent(doctorId)}&date=${encodeURIComponent(dateVal)}`)
      .then(res => res.json())
      .then(data => {
        if (!data.success) {
          slotContainer.innerHTML = `<p style="color: #DC2626; font-size: 0.875rem;">${data.error || 'Doctor does not work on this date (Doctors work Monday to Friday).'}</p>`;
          return;
        }

        if (!data.slots || data.slots.length === 0) {
          slotContainer.innerHTML = '<p style="color: #D97706; font-size: 0.875rem;">No available slots found for this date. The doctor may be fully booked or off duty. Please try another weekday.</p>';
          return;
        }

        let html = '<p style="font-size: 0.85rem; color: #475569; margin-bottom: 8px; font-weight: 600;">👇 Click on an available time slot below:</p>';
        html += '<div class="slot-grid">';
        data.slots.forEach(slot => {
          const isSelected = (prevTime === slot);
          html += `<button type="button" class="slot-btn ${isSelected ? 'selected' : ''}" data-time="${slot}">${slot}</button>`;
        });
        html += '</div>';
        html += '<div id="slotSelectedBanner" class="slot-selected-banner" style="' + (prevTime ? '' : 'display: none;') + '">✓ Selected Time: <strong id="slotSelectedTimeText">' + (prevTime || '') + '</strong></div>';
        slotContainer.innerHTML = html;

        // Attach click handlers to newly rendered slot buttons
        const buttons = slotContainer.querySelectorAll('.slot-btn');
        const banner = document.getElementById('slotSelectedBanner');
        const bannerText = document.getElementById('slotSelectedTimeText');

        buttons.forEach(btn => {
          btn.addEventListener('click', () => {
            buttons.forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            const chosenTime = btn.getAttribute('data-time');
            if (timeHiddenInput) {
              timeHiddenInput.value = chosenTime;
            }
            if (banner && bannerText) {
              bannerText.textContent = chosenTime;
              banner.style.display = 'flex';
            }
            slotContainer.style.borderColor = '#BFDBFE';
          });
        });
      })
      .catch(err => {
        slotContainer.innerHTML = '<p style="color: #DC2626; font-size: 0.875rem;">Error checking slots. Please try again.</p>';
      });
  }

  if (doctorSelect) doctorSelect.addEventListener('change', fetchSlots);
  if (dateInput) dateInput.addEventListener('change', fetchSlots);

  // Form submit validation for booking
  const bookingForm = document.getElementById('bookingForm');
  if (bookingForm) {
    bookingForm.addEventListener('submit', (e) => {
      if (!timeHiddenInput || !timeHiddenInput.value) {
        e.preventDefault();
        if (slotContainer) {
          slotContainer.style.borderColor = '#DC2626';
          slotContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        alert('⚠️ Please select an available appointment time slot before submitting.');
      }
    });
  }

  // If page loads with pre-filled inputs, run slot check automatically
  if (doctorSelect && dateInput && doctorSelect.value && dateInput.value) {
    fetchSlots();
  }

  // 2. Cryptographic Audit Chain Verification Button in Admin Portal
  const verifyBtn = document.getElementById('verifyAuditBtn');
  const verifyResult = document.getElementById('verifyResult');

  if (verifyBtn && verifyResult) {
    verifyBtn.addEventListener('click', () => {
      verifyResult.innerHTML = '<span style="color: #2563EB;">Verifying SHA-256 hash chains across all audit logs...</span>';
      fetch('/admin/api/verify-integrity')
        .then(res => res.json())
        .then(data => {
          if (data.valid) {
            verifyResult.innerHTML = `<span class="badge badge-verified" style="font-size: 0.9rem; padding: 6px 14px;">✓ ${data.message}</span>`;
          } else {
            verifyResult.innerHTML = `<span class="badge" style="background: #FEE2E2; color: #991B1B; font-size: 0.9rem;">⚠️ ${data.message}</span>`;
          }
        })
        .catch(err => {
          verifyResult.innerHTML = '<span style="color: #DC2626;">Verification check failed.</span>';
        });
    });
  }
});

