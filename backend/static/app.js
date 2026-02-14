const API = '';

const SIMULATED_MATCHES = [
  { user_a: 'Alex Chen', user_b: 'You', score: 92, reason: 'Shared interest in AI and startups' },
  { user_a: 'Jordan Taylor', user_b: 'You', score: 88, reason: 'Both love hiking and outdoor activities' },
  { user_a: 'Sam Rivera', user_b: 'You', score: 85, reason: 'Tech and gaming in common' },
  { user_a: 'Morgan Lee', user_b: 'You', score: 81, reason: 'Similar communication style and values' },
  { user_a: 'Casey Kim', user_b: 'You', score: 78, reason: 'Creative and design interests align' },
];

const ADDABLE_TOPICS = ['Finance', 'Politics', 'Science', 'Books', 'Music', 'Gaming', 'Startups', 'Travel', 'Food', 'Fitness', 'Art', 'Movies'];
const REACTION_EMOJIS = ['👍', '❤️', '😂', '🔥'];

function get(path) {
  return fetch(API + path).then(r => {
    if (!r.ok) throw new Error(r.statusText);
    return r.json();
  });
}

function post(path, body) {
  return fetch(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(r => {
    if (!r.ok) throw new Error(r.statusText);
    return r.json();
  });
}

function del(path) {
  return fetch(API + path, { method: 'DELETE' }).then(r => {
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

const chatMessagesEl = document.getElementById('chat-messages');
const humanInputArea = document.getElementById('human-input-area');
const matchDetailView = document.getElementById('match-detail-view');
let activeChatKey = 'human';
let addedTabs = [];
let selectedMatchIndex = null;
let matchesList = [];
let viewMode = 'chat'; // 'chat' | 'match'

function setActiveChat(chatKey) {
  activeChatKey = chatKey;
  viewMode = 'chat';
  matchDetailView.style.display = 'none';
  chatMessagesEl.style.display = 'block';
  humanInputArea.style.display = chatKey === 'human' ? 'block' : 'none';

  document.querySelectorAll('.nav-tab').forEach(b => {
    b.classList.toggle('active', b.dataset.chat === chatKey);
  });
  if (chatKey === 'human') loadHumanChat();
  else loadChat(chatKey);
}

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

function loadHumanChat() {
  chatMessagesEl.innerHTML = 'Loading…';
  get('/api/conversations/human')
    .then(data => {
      const messages = data.messages || [];
      if (messages.length === 0) {
        chatMessagesEl.innerHTML = '<p class="empty-msg">No messages yet. Say something! Claude will reply.</p>';
        return;
      }
      chatMessagesEl.innerHTML = renderMessages(messages, true);
    })
    .catch(() => {
      chatMessagesEl.innerHTML = '<p class="empty-msg">Could not load human chat.</p>';
    });
}

function renderMessages(messages, withReactions) {
  if (!messages || messages.length === 0) return '';
  return messages.map((m, idx) => {
    const id = m.id !== undefined ? m.id : idx;
    const reactions = m.reactions || {};
    const reactionHtml = withReactions
      ? '<div class="msg-reactions">' +
        Object.entries(reactions).map(([emoji, count]) =>
          '<span class="msg-reaction" data-msg-id="' + id + '" data-emoji="' + escapeHtml(emoji) + '">' + escapeHtml(emoji) + ' ' + count + '</span>'
        ).join('') +
        REACTION_EMOJIS.map(emoji =>
          '<button type="button" class="msg-reaction msg-reaction-add" data-msg-id="' + id + '" data-emoji="' + emoji + '" title="Add ' + emoji + '">' + emoji + '</button>'
        ).join('') +
        '</div>'
      : '';
    return (
      '<div class="chat-msg" data-msg-id="' + id + '">' +
      '<span class="speaker">' + escapeHtml(m.speaker) + '</span>' +
      '<span class="bubble">' + escapeHtml(m.text) + '</span>' +
      (m.timestamp ? '<div class="time">' + escapeHtml(m.timestamp) + '</div>' : '') +
      reactionHtml +
      '</div>'
    );
  }).join('');
}

function showMatchDetail() {
  if (selectedMatchIndex == null || !matchesList[selectedMatchIndex]) return;
  const m = matchesList[selectedMatchIndex];
  const name = escapeHtml(m.user_a);
  const score = Number(m.score);
  const reason = escapeHtml(m.reason || '');
  matchDetailView.innerHTML =
    '<div class="match-detail-card">' +
    '<h2>' + name + '</h2>' +
    '<span class="score-badge">' + score + '% Match</span>' +
    '<p style="margin: 16px 0 0; color: #4a5568;">' + reason + '</p>' +
    '<div class="match-detail-actions">' +
    '<button type="button" class="btn-secondary-match" id="btn-back-chat">← Back to chat</button>' +
    '<button type="button" class="btn-primary-match" id="btn-view-profile">View profile</button>' +
    '<button type="button" class="btn-primary-match" id="btn-send-request">Send connection request</button>' +
    '</div>' +
    '</div>';
  matchDetailView.style.display = 'block';
  chatMessagesEl.style.display = 'none';
  humanInputArea.style.display = 'none';

  document.getElementById('btn-back-chat').addEventListener('click', function() {
    viewMode = 'chat';
    matchDetailView.style.display = 'none';
    chatMessagesEl.style.display = 'block';
    if (activeChatKey === 'human') humanInputArea.style.display = 'block';
    loadHumanChat();
  });
  document.getElementById('btn-view-profile').addEventListener('click', function() {
    get('/api/personas').then(function(personas) {
      const p = personas.find(function(x) { return (x.name || '').toLowerCase() === (m.user_a || '').toLowerCase(); });
      if (p) {
        matchDetailView.querySelector('.match-detail-card').innerHTML +=
          '<div style="margin-top: 20px; padding: 16px; background: #fff; border-radius: 8px; border: 1px solid #E2E8F0;">' +
          '<strong>Profile</strong><p>' + escapeHtml(p.personality_summary || '') + '</p>' +
          '<p><strong>Interests:</strong> ' + escapeHtml((p.interests || []).join(', ')) + '</p></div>';
      } else {
        alert('No full profile found for ' + m.user_a + '. Match reason: ' + m.reason);
      }
    });
  });
  document.getElementById('btn-send-request').addEventListener('click', function() {
    post('/api/connection-requests', { to: m.user_a })
      .then(function() { alert('Connection request sent to ' + m.user_a + '!'); })
      .catch(function(err) { alert(err.message); });
  });
}

function loadMatches() {
  const el = document.getElementById('matches-list');
  get('/api/matches')
    .then(data => {
      matchesList = Array.isArray(data) ? data : [];
      if (matchesList.length === 0) matchesList = SIMULATED_MATCHES;
      el.innerHTML = matchesList.map((m, idx) => {
        const name = escapeHtml(m.user_a);
        const score = Number(m.score);
        const reason = escapeHtml(m.reason || '');
        const activeClass = selectedMatchIndex === idx ? ' active' : '';
        return (
          '<div class="match-card' + activeClass + '" data-match-index="' + idx + '">' +
          '<div class="match-score-row"><span class="match-name">' + name + '</span><span class="score-badge">' + score + '% Match</span></div>' +
          '<div class="match-details"><div class="detail-item"><div class="detail-label">💬 Why you\'ll connect</div><div class="detail-value">' + reason + '</div></div></div>' +
          '<div class="conversation-preview"><h4>💡 Compatibility</h4><p>' + reason + '</p></div>' +
          '</div>'
        );
      }).join('');
      el.querySelectorAll('.match-card').forEach(function(card) {
        card.addEventListener('click', function() {
          selectedMatchIndex = parseInt(this.dataset.matchIndex, 10);
          el.querySelectorAll('.match-card').forEach(function(c) { c.classList.remove('active'); });
          this.classList.add('active');
          showMatchDetail();
        });
      });
    })
    .catch(function() {
      matchesList = SIMULATED_MATCHES;
      el.innerHTML = SIMULATED_MATCHES.map(function(m, idx) {
        const name = escapeHtml(m.user_a);
        const reason = escapeHtml(m.reason || '');
        const activeClass = selectedMatchIndex === idx ? ' active' : '';
        return (
          '<div class="match-card' + activeClass + '" data-match-index="' + idx + '">' +
          '<div class="match-score-row"><span class="match-name">' + name + '</span><span class="score-badge">' + m.score + '% Match</span></div>' +
          '<div class="match-details"><div class="detail-item"><div class="detail-label">💬 Why you\'ll connect</div><div class="detail-value">' + reason + '</div></div></div>' +
          '<div class="conversation-preview"><h4>💡 Compatibility</h4><p>' + reason + '</p></div></div>'
        );
      }).join('');
      el.querySelectorAll('.match-card').forEach(function(card) {
        card.addEventListener('click', function() {
          selectedMatchIndex = parseInt(this.dataset.matchIndex, 10);
          el.querySelectorAll('.match-card').forEach(function(c) { c.classList.remove('active'); });
          this.classList.add('active');
          showMatchDetail();
        });
      });
    });
}

document.querySelectorAll('.nav-tab').forEach(function(btn) {
  if (btn.id === 'tab-add') return;
  btn.addEventListener('click', function() { setActiveChat(btn.dataset.chat); });
});

const tabAddBtn = document.getElementById('tab-add');
const addTopicDropdown = document.getElementById('add-topic-dropdown');
const addTopicList = document.getElementById('add-topic-list');
const dynamicTabs = document.getElementById('dynamic-tabs');

ADDABLE_TOPICS.forEach(function(topic, i) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'add-topic-item';
  btn.textContent = topic;
  btn.dataset.topic = topic;
  btn.addEventListener('click', function() {
    if (addedTabs.includes(topic)) return;
    addedTabs.push(topic);
    const key = topic.toLowerCase();
    const tab = document.createElement('button');
    tab.type = 'button';
    tab.className = 'nav-tab';
    tab.dataset.chat = key;
    tab.textContent = topic;
    tab.addEventListener('click', function() { setActiveChat(key); });
    dynamicTabs.appendChild(tab);
    addTopicDropdown.style.display = 'none';
    setActiveChat(key);
  });
  addTopicList.appendChild(btn);
});

tabAddBtn.addEventListener('click', function(e) {
  e.stopPropagation();
  var show = addTopicDropdown.style.display !== 'block';
  addTopicDropdown.style.display = show ? 'block' : 'none';
  addTopicList.querySelectorAll('.add-topic-item').forEach(function(btn) {
    btn.style.display = addedTabs.includes(btn.dataset.topic) ? 'none' : 'block';
  });
});

document.addEventListener('click', function() {
  addTopicDropdown.style.display = 'none';
});
addTopicDropdown.addEventListener('click', function(e) {
  e.stopPropagation();
});

document.getElementById('human-form').addEventListener('submit', function(e) {
  e.preventDefault();
  var text = document.getElementById('human-text').value.trim();
  if (!text) return;
  post('/api/conversations/human', { text: text })
    .then(function(res) {
      document.getElementById('human-text').value = '';
      if (res.messages) {
        chatMessagesEl.innerHTML = renderMessages(res.messages, true);
      } else {
        loadHumanChat();
      }
    })
    .catch(function(err) { alert(err.message); });
});

document.getElementById('human-clear').addEventListener('click', function() {
  if (!confirm('Clear all human chat messages?')) return;
  del('/api/conversations/human')
    .then(function() { loadHumanChat(); })
    .catch(function(err) { alert(err.message); });
});

loadMatches();
setActiveChat('human');

// Bind reaction buttons after first human chat load (and after any re-render)
setTimeout(function() {
  chatMessagesEl.addEventListener('click', function(e) {
    if (e.target.classList.contains('msg-reaction-add')) {
      var msgId = parseInt(e.target.dataset.msgId, 10);
      var emoji = e.target.dataset.emoji;
      post('/api/conversations/human/react', { message_id: msgId, emoji: emoji })
        .then(function() { loadHumanChat(); })
        .catch(function(err) { alert(err.message); });
    }
  });
}, 100);
