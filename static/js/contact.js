// Salve como: static/js/contact.js
// VERSÃO ADAPTADA PARA O ENVIO FETCH/AJAX DO FORMSPREE

(function () {
  'use strict';
  
  function qs(id) { return document.getElementById(id); }

  // Elementos do Modal
  const btnContact = qs('btn-contact');
  const modal = qs('modal-contato');
  const btnClose = qs('btn-close-modal');
  
  // Elementos do Formulário
  const contactForm = qs('contact-request-form');
  const contactResult = qs('contact-form-result'); // Elemento para feedback de status
  const contactMessage = qs('contactMessage');
  const msgCount = qs('msgCount');

  // --- Funções do Modal ---
  function openModal() {
    if (modal) {
      modal.setAttribute('aria-hidden', 'false');
    } else {
      console.error("HTML do 'modal-contato' não encontrado.");
    }
  }

  function closeModal() {
    if (modal) {
      modal.setAttribute('aria-hidden', 'true');
    }
    if (contactResult) {
      contactResult.textContent = ''; // Limpa msg de status
      contactResult.style.color = 'black'; // Reseta a cor
    }
    if (contactForm) {
      contactForm.reset(); // Limpa o formulário
    }
    if(msgCount) {
       msgCount.textContent = '0 / 500 caracteres'; // Reseta contagem
    }
  }

  // O listener de clique é anexado
  if (btnContact) {
      btnContact.addEventListener('click', openModal);
  } else {
      console.warn("Botão de contato 'btn-contact' não encontrado.");
      return; 
  }
  
  if (btnClose) {
    btnClose.addEventListener('click', closeModal);
  }
  
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
          closeModal();
      }
    });
  }

  // Contagem de caracteres
  if (contactMessage && msgCount) {
    contactMessage.addEventListener('input', () => {
      const len = contactMessage.value.length;
      msgCount.textContent = `${len} / 500 caracteres`;
    });
  }

  // --- Lógica de Envio (Adaptada do seu Formspree Script) ---
  
  async function handleSubmit(event) {
    event.preventDefault(); // Impede o envio tradicional
    
    // Mostra o status de envio
    contactResult.style.color = 'black';
    contactResult.textContent = 'Enviando...';
    
    // Usa FormData para coletar todos os campos que têm o atributo 'name'
    var data = new FormData(event.target);
    
    try {
        const response = await fetch(event.target.action, {
            method: contactForm.method,
            body: data,
            headers: {
                'Accept': 'application/json' // Header necessário para Formspree AJAX
            }
        });

        if (response.ok) {
            contactResult.style.color = 'green';
            contactResult.textContent = "Mensagem recebida! Obrigado.";
            contactForm.reset();
            // Fecha o modal após o sucesso
            setTimeout(closeModal, 2000); 
        } else {
            const data = await response.json();
            contactResult.style.color = 'red';
            
            if (Object.hasOwn(data, 'errors')) {
                // Erros de validação do Formspree
                contactResult.textContent = data["errors"].map(error => error["message"]).join(", ");
            } else {
                contactResult.textContent = "Ops! Houve um problema ao enviar seu formulário.";
            }
        }
    } catch (error) {
        contactResult.style.color = 'red';
        contactResult.textContent = "Ops! Houve um problema de comunicação ao enviar o formulário.";
        console.error("Fetch/Formspree Error:", error);
    }
  }

  // Anexa o listener de submissão do formulário
  if (contactForm) {
    contactForm.addEventListener("submit", handleSubmit);
  }
})();