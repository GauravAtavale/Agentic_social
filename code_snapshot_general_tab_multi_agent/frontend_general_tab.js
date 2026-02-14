/**
 * General tab multi-agent: loadChat() changes and generateGeneralConversation().
 * Merge into backend/static/app.js.
 */

// --- Replace loadChat() with this version ---
function loadChat(group) {
  chatMessagesEl.innerHTML = 'Loading…';
  get(`/api/conversations/${group}`)
    .then(data => {
      if (!data || !data.messages || data.messages.length === 0) {
        if (group === 'general') {
          chatMessagesEl.innerHTML =
            '<p class="empty-msg">No multi-agent conversation yet.</p>' +
            '<button type="button" class="btn-generate-general" id="btn-generate-general">Generate conversation (multi-agent)</button>';
          document.getElementById('btn-generate-general').addEventListener('click', generateGeneralConversation);
          return;
        }
        chatMessagesEl.innerHTML = '<p class="empty-msg">No conversation for this topic yet.</p>';
        return;
      }
      chatMessagesEl.innerHTML = renderMessages(data.messages, false);
    })
    .catch(() => {
      chatMessagesEl.innerHTML = '<p class="empty-msg">No conversation for this topic yet.</p>';
    });
}

// --- Add this new function (after loadChat) ---
function generateGeneralConversation() {
  const btn = document.getElementById('btn-generate-general');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Generating…';
  }
  chatMessagesEl.innerHTML = '<p class="empty-msg">Generating multi-agent chat (personas taking turns)…</p>';
  fetch(API + '/api/conversations/general/generate?turns=10', { method: 'POST' })
    .then(r => {
      if (!r.ok) throw new Error(r.statusText);
      return r.json();
    })
    .then(res => {
      const messages = res.messages || [];
      if (messages.length === 0) {
        chatMessagesEl.innerHTML = '<p class="empty-msg">No messages generated. Add personas first (Profile → Create persona).</p>';
        return;
      }
      chatMessagesEl.innerHTML = renderMessages(messages, false);
    })
    .catch(err => {
      chatMessagesEl.innerHTML = '<p class="empty-msg">Error: ' + escapeHtml(err.message) + '</p>' +
        '<button type="button" class="btn-generate-general" id="btn-generate-general">Retry</button>';
      document.getElementById('btn-generate-general').addEventListener('click', generateGeneralConversation);
    });
}
