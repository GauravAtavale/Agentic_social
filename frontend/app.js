(function () {
  const chatMessagesEl = document.getElementById('chat-messages');

  function get(path) {
    return fetch(path).then(function (r) {
      if (!r.ok) throw new Error(r.statusText);
      return r.json();
    });
  }

  function escapeHtml(s) {
    if (s == null) return '';
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  function appendOneMessage(role, content) {
    const wrap = document.createElement('div');
    wrap.className = 'chat-msg';
    wrap.innerHTML =
      '<span class="speaker">' + escapeHtml(role || 'Unknown') + '</span>' +
      '<span class="bubble">' + escapeHtml(content || '') + '</span>';
    chatMessagesEl.appendChild(wrap);
    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
  }

  function renderAll(messages) {
    if (!messages || messages.length === 0) return;
    messages.forEach(function (m) {
      appendOneMessage(m.role || m.speaker, m.content || m.text);
    });
  }

  // Initial load: fetch history and render
  get('/api/history').then(function (data) {
    const messages = (data && data.messages) || [];
    chatMessagesEl.innerHTML = '';
    if (messages.length === 0) {
      chatMessagesEl.innerHTML = '<p class="empty-msg">Waiting for messages… run.py is writing to conversational_history.txt.</p>';
    } else {
      renderAll(messages);
    }
    // Stream new lines as they appear in the file
    const evtSource = new EventSource('/api/history/stream');
    evtSource.onmessage = function (e) {
      const empty = chatMessagesEl.querySelector('.empty-msg');
      if (empty) empty.remove();
      try {
        const ev = JSON.parse(e.data);
        if (ev.type === 'message' && (ev.role || ev.content)) {
          appendOneMessage(ev.role, ev.content);
        }
      } catch (err) {}
    };
    evtSource.onerror = function () {
      evtSource.close();
    };
  }).catch(function (err) {
    chatMessagesEl.innerHTML = '<p class="empty-msg">Error: ' + escapeHtml(err.message) + '</p>';
  });
})();
