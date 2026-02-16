(function() {
  const form = document.getElementById('questionnaireForm');
  const afterSubmit = document.getElementById('after-submit');
  const progressBar = document.getElementById('progressBar');
  const voiceQuestionsEl = document.getElementById('voice-questions');
  const createPersonaBtn = document.getElementById('createPersonaBtn');
  const createPersonaStatus = document.getElementById('createPersonaStatus');

  let savedProfile = null;
  let conversation = [];
  let mediaRecorder = null;
  let currentStream = null;
  let recordedChunks = [];
  let currentQuestionIndex = -1;

  form.addEventListener('change', function() {
    const inputs = form.querySelectorAll('input[required], select');
    let filled = 0;
    inputs.forEach(function(el) {
      if (el.value && el.value.trim()) filled++;
    });
    progressBar.style.width = Math.min(100, (filled / 3) * 100) + '%';
  });

  form.addEventListener('submit', function(e) {
    e.preventDefault();
    const fd = new FormData(form);
    const profile = {
      profile: {
        fullName: fd.get('fullName') || '',
        email: fd.get('email') || '',
        location: fd.get('location') || ''
      },
      professional: {
        jobTitle: fd.get('jobTitle') || '',
        company: fd.get('company') || '',
        skills: (fd.get('skills') || '').split(',').map(s => s.trim()).filter(Boolean)
      },
      interests: (fd.get('interests') || '').split(',').map(s => s.trim()).filter(Boolean),
      weekend: fd.get('weekend') || '',
      socialEnergy: fd.get('socialEnergy') || '',
      communicationStyle: fd.get('commStyle') || '',
      seeking: fd.get('seeking') || ''
    };
    savedProfile = profile;

    fetch('/api/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile)
    })
      .then(function(r) {
        if (!r.ok) throw new Error('Save failed');
        return r.json();
      })
      .then(function() {
        form.style.display = 'none';
        afterSubmit.style.display = 'block';
        loadVoiceQuestions();
      })
      .catch(function(err) {
        alert('Could not save profile: ' + err.message);
      });
  });

  function loadVoiceQuestions() {
    voiceQuestionsEl.innerHTML = '<p>Loading questions…</p>';
    fetch('/api/questions')
      .then(function(r) { return r.json(); })
      .then(function(data) {
        const questions = data.questions || [];
        conversation = questions.map(function(q) { return { question: q, answer: '' }; });
        voiceQuestionsEl.innerHTML = questions.map(function(q, i) {
          return (
            '<div class="voice-q-block" data-index="' + i + '">' +
              '<div class="voice-q-text">' + escapeHtml(q) + '</div>' +
              '<div class="voice-q-actions">' +
                '<button type="button" class="btn-record" data-index="' + i + '">Record</button>' +
                '<button type="button" class="btn-stop" data-index="' + i + '" style="display:none;">Stop</button>' +
              '</div>' +
              '<div class="voice-q-answer" data-index="' + i + '"></div>' +
            '</div>'
          );
        }).join('');

        voiceQuestionsEl.querySelectorAll('.btn-record').forEach(function(btn) {
          btn.addEventListener('click', function() {
            startRecording(parseInt(this.dataset.index, 10));
          });
        });
        voiceQuestionsEl.querySelectorAll('.btn-stop').forEach(function(btn) {
          btn.addEventListener('click', function() {
            stopRecording(parseInt(this.dataset.index, 10));
          });
        });
      })
      .catch(function() {
        voiceQuestionsEl.innerHTML = '<p class="error-msg">Could not load questions. You can still create your persona from your profile.</p>';
        conversation = [];
      });
  }

  function escapeHtml(s) {
    if (s == null) return '';
    var div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  function startRecording(index) {
    currentQuestionIndex = index;
    recordedChunks = [];
    var block = voiceQuestionsEl.querySelector('.voice-q-block[data-index="' + index + '"]');
    block.querySelector('.btn-record').style.display = 'none';
    block.querySelector('.btn-stop').style.display = 'inline-block';
    block.querySelector('.voice-q-answer').textContent = 'Recording…';

    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(function(stream) {
        currentStream = stream;
        var options = { mimeType: 'audio/webm' };
        if (!MediaRecorder.isTypeSupported('audio/webm')) {
          options = {};
        }
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = function(e) {
          if (e.data.size > 0) recordedChunks.push(e.data);
        };
        mediaRecorder.start();
      })
      .catch(function(err) {
        block.querySelector('.btn-record').style.display = 'inline-block';
        block.querySelector('.btn-stop').style.display = 'none';
        block.querySelector('.voice-q-answer').textContent = 'Error: ' + (err.message || 'Microphone access denied');
      });
  }

  function stopRecording(index) {
    if (!mediaRecorder || mediaRecorder.state === 'inactive') return;
    var block = voiceQuestionsEl.querySelector('.voice-q-block[data-index="' + index + '"]');
    block.querySelector('.btn-record').style.display = 'inline-block';
    block.querySelector('.btn-stop').style.display = 'none';
    block.querySelector('.voice-q-answer').textContent = 'Transcribing…';

    mediaRecorder.onstop = function() {
      if (currentStream) {
        currentStream.getTracks().forEach(function(t) { t.stop(); });
        currentStream = null;
      }
      var blob = new Blob(recordedChunks, { type: 'audio/webm' });
      var reader = new FileReader();
      reader.onload = function() {
        var dataUrl = reader.result;
        var base64 = dataUrl.indexOf(',') >= 0 ? dataUrl.split(',')[1] : dataUrl;
        fetch('/api/transcribe', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ audio_base64: base64 })
        })
          .then(function(r) {
            if (!r.ok) return r.json().then(function(d) { throw new Error(d.detail || 'Transcribe failed'); });
            return r.json();
          })
          .then(function(data) {
            var text = (data.text || '').trim();
            conversation[index].answer = text;
            block.querySelector('.voice-q-answer').textContent = text || '(no speech detected)';
          })
          .catch(function(err) {
            block.querySelector('.voice-q-answer').textContent = 'Error: ' + (err.message || 'Transcription failed');
          });
      };
      reader.readAsDataURL(blob);
    };
    mediaRecorder.stop();
  }

  createPersonaBtn.addEventListener('click', function() {
    if (!savedProfile) {
      createPersonaStatus.textContent = 'Submit the profile form first.';
      createPersonaStatus.className = 'status-msg error';
      return;
    }

    var convToSend = conversation.filter(function(c) { return c.answer; });
    if (convToSend.length === 0) {
      convToSend = null;
    }

    createPersonaBtn.disabled = true;
    createPersonaStatus.textContent = 'Creating your persona…';
    createPersonaStatus.className = 'status-msg';

    fetch('/api/create-persona', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile: savedProfile, conversation: convToSend })
    })
      .then(function(r) {
        if (!r.ok) return r.json().then(function(d) { throw new Error(d.detail || 'Failed'); });
        return r.json();
      })
      .then(function() {
        createPersonaStatus.textContent = 'Persona created! Redirecting…';
        createPersonaStatus.className = 'status-msg success';
        setTimeout(function() { window.location.href = '/'; }, 1200);
      })
      .catch(function(err) {
        createPersonaStatus.textContent = 'Error: ' + (err.message || 'Could not create persona');
        createPersonaStatus.className = 'status-msg error';
        createPersonaBtn.disabled = false;
      });
  });
})();
