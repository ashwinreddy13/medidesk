document.addEventListener('DOMContentLoaded', () => {
  const trigger = document.getElementById('assistantTrigger');
  const modal = document.getElementById('assistantModal');
  const closeBtn = document.getElementById('closeAssistantBtn');
  const sendBtn = document.getElementById('assistantSendBtn');
  const input = document.getElementById('assistantInput');
  const chatBody = document.getElementById('assistantChatBody');
  const quickChips = document.querySelectorAll('.quick-chip');

  if (!trigger || !modal) return;

  function toggleModal() {
    modal.classList.toggle('open');
    if (modal.classList.contains('open') && input) {
      input.focus();
    }
  }

  trigger.addEventListener('click', toggleModal);
  if (closeBtn) closeBtn.addEventListener('click', toggleModal);

  function appendMessage(sender, text, actionUrl = null) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${sender}`;
    
    // Convert newlines to breaks
    const formatted = text.replace(/\n/g, '<br>');
    bubble.innerHTML = formatted;

    if (actionUrl) {
      const linkBtn = document.createElement('div');
      linkBtn.style.marginTop = '8px';
      linkBtn.innerHTML = `<a href="${actionUrl}" class="btn btn-sm btn-primary">Go to page →</a>`;
      bubble.appendChild(linkBtn);
    }

    chatBody.appendChild(bubble);
    chatBody.scrollTop = chatBody.scrollHeight;
  }

  function sendMessage(queryText) {
    const text = (queryText || (input ? input.value : '')).trim();
    if (!text) return;

    appendMessage('user', text);
    if (input) input.value = '';

    // Typing placeholder
    const typingBubble = document.createElement('div');
    typingBubble.className = 'chat-bubble assistant';
    typingBubble.id = 'assistantTyping';
    typingBubble.innerHTML = '<em>MediDesk Assistant is thinking...</em>';
    chatBody.appendChild(typingBubble);
    chatBody.scrollTop = chatBody.scrollHeight;

    fetch('/assistant/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: text })
    })
      .then(res => res.json())
      .then(data => {
        const placeholder = document.getElementById('assistantTyping');
        if (placeholder) placeholder.remove();
        appendMessage('assistant', data.response, data.suggestion_action);
      })
      .catch(err => {
        const placeholder = document.getElementById('assistantTyping');
        if (placeholder) placeholder.remove();
        appendMessage('assistant', "I'm having trouble connecting right now. Please try again in a moment.");
      });
  }

  if (sendBtn) {
    sendBtn.addEventListener('click', () => sendMessage());
  }

  if (input) {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        sendMessage();
      }
    });
  }

  quickChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const query = chip.getAttribute('data-query');
      if (query) sendMessage(query);
    });
  });
});

