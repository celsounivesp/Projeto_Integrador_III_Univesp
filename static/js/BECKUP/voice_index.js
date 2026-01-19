// Salve como: static/js/voice_index.js
// (Versão COMPLETA E CORRIGIDA: 332 Linhas)

(function () {
  // --- 1. Selecionar todos os elementos ---
  const btnMic = document.getElementById("btnMic");
  const formVoz = document.getElementById("formVoz");
  const iosDict = document.getElementById("iosDict");
  const tapSound = document.getElementById("tapSound");
  const ttsPlayer = document.getElementById("ttsPlayer");
  const resultsContainer = document.getElementById("resultsContainer");
  const telaMic = document.getElementById("telaMic"); // Tela principal

  const welcomeTtsUrl = document.body.getAttribute("data-tts") || "";
  let audioUnlocked = false; // (Usado para o 'primeiro clique' genérico)

  // --- 2. Funções de Áudio e UI ---

  /**
   * (NOVO) Interrompe qualquer áudio que esteja tocando.
   */
  function stopTTS() {
    if (ttsPlayer) {
      ttsPlayer.pause();
      ttsPlayer.src = '';
    }
  }

  function playTTS(url) {
    stopTTS(); // Para o áudio anterior antes de tocar o novo
    if (!url || !ttsPlayer) return;
    try {
      ttsPlayer.src = url;
      ttsPlayer.play().catch((e) => console.error("Erro ao tocar TTS:", e));
    } catch (e) {
      console.error("Falha no player:", e);
    }
  }

  /**
   * (MODIFICADO) Esta função agora SÓ destrava o áudio
   * para o AUTOPLAY funcionar, caso o usuário clique
   * fora do microfone.
   */
  function firstGestureUnlock() {
    if (audioUnlocked) return;
    audioUnlocked = true;

    try {
      if (tapSound) {
        tapSound.currentTime = 0;
        tapSound.play().catch(() => {});
      }
    } catch (e) {}
    
    // O autoplay está no HTML.
    
    document.removeEventListener("touchstart", firstGestureUnlock, { passive: true });
    document.removeEventListener("click", firstGestureUnlock, true);
  }

  async function returnToHomeAndPlayAudio() {
    if (resultsContainer) resultsContainer.innerHTML = "";
    if (iosDict) iosDict.value = "";
    if (telaMic) telaMic.style.display = "block";
    
    try {
      const response = await fetch('/api/tts/welcome_back');
      const data = await response.json();
      if (data.ok && data.tts_url) {
        playTTS(data.tts_url); // 'playTTS' já interrompe áudios anteriores
      }
    } catch (e) {
      console.error("Falha ao buscar áudio de 'welcome_back':", e);
    }
  }

  /**
   * Renderiza os cards de resultado ou a tela de erro.
   */
  function renderResults(data) {
    if (!resultsContainer) {
      console.error("ERRO: <div id='resultsContainer'> não encontrado.");
      return;
    }
    
    if (telaMic) telaMic.style.display = "none";

    // Se OK (data.ok é true), renderiza os cards
    if (data.ok && data.cards && data.cards.length > 0) {
      let html = `<h2>${data.cards[0].destino.toUpperCase()}</h2>`;
      
      data.cards.forEach(card => {
        html += `
          <div class="card">
            <div class="card-num">${card.idx}</div>
            <div class="card-info">
              <div class="card-sentido">SENTIDO: ${card.sentido}</div>
              <div class="line">
                <span class="line-highlight">LINHA ${card.linha}</span> • ${card.horario} • ${card.eta} min
              </div>
              <div class="card-ponto">PONTO: ${card.ponto}</div>
            </div>
          </div>
        `;
      });
      // (CORRIGIDO) Usa .png para os ícones
      html += `
        <div class="actions">
          <button id="btnRepetir" class="action-btn" aria-label="Repetir Áudio">
            <img src="/static/img/btn_repeat.png" alt="Repetir Áudio">
          </button>
          <button id="btnNovaConsulta" class="action-btn" aria-label="Nova Consulta">
            <img src="/static/img/btn_new.png" alt="Nova Consulta">
          </button>
        </div>
      `;
      resultsContainer.innerHTML = html;

      // Adiciona listeners aos botões de sucesso
      document.getElementById("btnRepetir").addEventListener("click", () => {
        playTTS(data.tts_url);
      });
      document.getElementById("btnNovaConsulta").addEventListener("click", () => {
        stopTTS(); 
        returnToHomeAndPlayAudio();
      });
    } 
    // (MODIFICADO) Se NÃO OK e é o erro 'show_call_button'
    else if (!data.ok && data.show_call_button) {
      let html = `
        <p class="error-msg">${data.msg || "Erro"}</p>
        
        <img src="/static/img/logo_dest.png" alt="Destino não encontrado" class="error-image-dest">

        <div class="actions">
          <a href="tel:08001218484" class="action-btn" aria-label="Ligar Pira Mobilidade" id="btnLigarPira">
            <img src="/static/img/logo_pira.png" alt="Ligar Pira Mobilidade">
          </a>
          <button id="btnVoltarInicio" class="action-btn" aria-label="Voltar à Tela Inicial">
            <img src="/static/img/btn_new.png" alt="Voltar à Tela Inicial">
          </button>
        </div>
      `;
      resultsContainer.innerHTML = html;

      // Adiciona listener ao botão de ligar
      document.getElementById("btnLigarPira").addEventListener("click", () => {
         stopTTS(); 
      });
      // Adiciona listener ao botão de voltar
      document.getElementById("btnVoltarInicio").addEventListener("click", () => {
        stopTTS(); 
        returnToHomeAndPlayAudio();
      });
    }
    // Se for qualquer outro erro
    else if (!data.ok) {
      let html = `
        <p class="error-msg">${data.msg || "Ocorreu um erro."}</p>
        <div class="actions">
           <button id="btnVoltarInicio" class="action-btn" aria-label="Voltar à Tela Inicial">
             <img src="/static/img/btn_new.png" alt="Voltar à Tela Inicial">
           </button>
        </div>
      `;
      resultsContainer.innerHTML = html;
      document.getElementById("btnVoltarInicio").addEventListener("click", () => {
        stopTTS(); 
        returnToHomeAndPlayAudio();
      });
    }
  }

  /**
   * Envia a busca para o servidor usando fetch()
   */
  async function handleSearch(query) {
    if (btnMic) btnMic.disabled = true;

    try {
      const response = await fetch(formVoz.action, {
        method: formVoz.method,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ q: query || "" })
      });

      const data = await response.json();

      if (data.tts_url) {
        playTTS(data.tts_url);
      }

      renderResults(data);

    } catch (err) {
      console.error("Falha no fetch:", err);
      renderResults({ ok: false, msg: "Falha de conexão. Tente novamente." });
    }

    if (btnMic) btnMic.disabled = false;
  }

  /**
   * (MODIFICADO) Inicia o reconhecimento de voz.
   */
  function onMicPress(e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    
    // (MODIFICADO) CORREÇÃO DO BUG:
    // Para o áudio de boas-vindas imediatamente
    // ANTES de abrir o microfone.
    stopTTS(); 
    
    firstGestureUnlock(); // Garante que o áudio está liberado (se for o 1º clique)
    
    // Toca o som de 'tap'
    try { if (tapSound){ tapSound.currentTime = 0; tapSound.play().catch(()=>{}); } } catch(e){}

    const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Rec) {
      showIOSControls(); // Fallback para digitação
      return;
    }

    const rec = new Rec();
    rec.lang = "pt-BR";
    rec.interimResults = false;
    rec.maxAlternatives = 1;

    // --- (NOVO) VIBRAÇÃO ---
    rec.onstart = () => {
      // Vibra continuamente enquanto ouve
      if (navigator.vibrate) {
        navigator.vibrate([200, 100, 200, 100, 200, 100, 200, 100, 200, 100]); // Padrão de pulso
      }
    };
    
    rec.onend = () => {
      // Para a vibração quando o microfone fecha
      if (navigator.vibrate) {
        navigator.vibrate(0);
      }
    };
    // --- FIM VIBRAÇÃO ---

    // QUANDO TIVER UM RESULTADO
    rec.onresult = (ev) => {
      if (navigator.vibrate) navigator.vibrate(0); // Para vibração
      const txt = ev.results[0][0].transcript || "";
      if (iosDict) iosDict.value = txt;
      handleSearch(txt); // <--- CHAMA A FUNÇÃO DE BUSCA (fetch)
    };

    // SE O RECONHECIMENTO FALHAR
    rec.onerror = (err) => {
      if (navigator.vibrate) navigator.vibrate(0); // Para vibração
      console.error("SpeechRecognition error:", err);
      if (err.error === 'no-speech' || err.error === 'audio-capture') {
        handleSearch(""); // Envia busca vazia (servidor responderá "Nenhum destino informado")
      } else {
        showIOSControls(); // Fallback para digitação se for outro erro
      }
    };

    try {
      rec.start();
    } catch (err) {
      console.error("rec.start() failed:", err);
      showIOSControls(); // Fallback para digitação
    }
  }

  /**
   * Mostra os controles de digitação (fallback para iOS/erros)
   */
  function showIOSControls() {
    if (iosDict) {
      iosDict.style.display = "block";
      iosDict.focus();
    }
    const ctrl = document.getElementById("iosControls");
    if (ctrl) ctrl.style.display = "block";
  }

  // --- 3. Anexar os Event Listeners ---

  // Listener para o microfone
  if (btnMic) {
    // Usamos 'mousedown' ou 'touchstart' para resposta rápida
    btnMic.addEventListener("mousedown", onMicPress, { passive: false });
    btnMic.addEventListener("touchstart", onMicPress, { passive: false });
  }

  // Listener para o formulário (impede o submit padrão)
  if (formVoz) {
    formVoz.addEventListener("submit", (e) => {
      e.preventDefault(); // <--- CORREÇÃO IMPORTANTE
      const query = (iosDict ? iosDict.value : "").trim();
      handleSearch(query); // Chama a busca via fetch
    });
  }
  
  // Listeners para o primeiro toque/clique (desbloqueio de áudio)
  // (MODIFICADO) Agora só destrava o áudio, não toca o welcome.
  document.addEventListener("touchstart", firstGestureUnlock, { passive: true });
  document.addEventListener("click", firstGestureUnlock, true);

})();