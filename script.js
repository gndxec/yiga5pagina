document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener('click', (event) => {
    const targetId = anchor.getAttribute('href');
    const section = document.querySelector(targetId);

    if (!section) {
      return;
    }

    event.preventDefault();
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
});

const plansTrack = document.getElementById('plans-carousel-track');
const plansPrev = document.querySelector('.plans-arrow-prev');
const plansNext = document.querySelector('.plans-arrow-next');

if (plansTrack && plansPrev && plansNext) {
  plansNext.addEventListener('click', () => {
    const firstCard = plansTrack.firstElementChild;

    if (firstCard) {
      plansTrack.appendChild(firstCard);
    }
  });

  plansPrev.addEventListener('click', () => {
    const lastCard = plansTrack.lastElementChild;

    if (lastCard) {
      plansTrack.prepend(lastCard);
    }
  });
}

const leadAlertsHost = document.getElementById('lead-alerts');

if (leadAlertsHost) {
  const clientNames = [
    'María José',
    'Carlos Andrade',
    'Lian Mejia',
    'Adrian Changalombo',
    'Christian Burgos',
    'Douglas Coronado',
    'Juan GOnzalez',
    'Javier M.',
    'Daniela Torres',
    'Ricardo P.',
    'Camila Reyes',
    'Luis Fernando',
    'Valeria C.',
    'Jonathan V.',
    'Johan Gómez',
    'Sofía Martínez',
    'Andrés F.',
    'Isabella R.',
    'Diego L.',
    'Natalia S.',
    'Sebastián M.',
  ];

  const clientMessages = [
    'está consultando cobertura en su sector.',
    'pidió información del plan Protector 1000 Mbps.',
    'quiere contratar internet para su hogar.',
    'está revisando planes para teletrabajo.',
    'solicitó asesoría para instalación rápida.',
    'preguntó por disponibilidad en su zona.',
    'inició chat para contratar hoy mismo.'
  ];

  let audioContext;
  let audioReady = false;

  const randomItem = (list) => list[Math.floor(Math.random() * list.length)];

  const unlockAudio = async () => {
    if (audioReady) {
      return;
    }

    const AudioCtx = window.AudioContext || window.webkitAudioContext;

    if (!AudioCtx) {
      return;
    }

    audioContext = audioContext || new AudioCtx();

    try {
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
      }

      audioReady = true;
    } catch (_) {
      audioReady = false;
    }
  };

  const playBell = () => {
    if (!audioReady || !audioContext) {
      return;
    }

    const now = audioContext.currentTime;
    const frequencies = [1046.5, 1318.5];

    frequencies.forEach((frequency, index) => {
      const oscillator = audioContext.createOscillator();
      const gain = audioContext.createGain();

      oscillator.type = 'triangle';
      oscillator.frequency.value = frequency;

      gain.gain.setValueAtTime(0.0001, now + index * 0.06);
      gain.gain.exponentialRampToValueAtTime(0.15, now + 0.01 + index * 0.06);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.42 + index * 0.06);

      oscillator.connect(gain);
      gain.connect(audioContext.destination);

      oscillator.start(now + index * 0.06);
      oscillator.stop(now + 0.35 + index * 0.06);
    });
  };

  const showLeadAlert = () => {
    const name = randomItem(clientNames);
    const message = randomItem(clientMessages);

    const alert = document.createElement('article');
    alert.className = 'lead-alert';
    alert.innerHTML = `
      <div class="lead-alert-avatar" aria-hidden="true">🔔</div>
      <div>
        <strong>🔔 ${name}</strong>
        <span>${message}</span>
        <em>Hace unos segundos</em>
      </div>
    `;

    leadAlertsHost.prepend(alert);

    if (leadAlertsHost.children.length > 2) {
      leadAlertsHost.lastElementChild.remove();
    }

    requestAnimationFrame(() => {
      alert.classList.add('is-visible');
    });

    playBell();

    window.setTimeout(() => {
      alert.classList.remove('is-visible');
      window.setTimeout(() => {
        if (alert.parentElement) {
          alert.remove();
        }
      }, 320);
    }, 6500);
  };

  ['click', 'touchstart', 'keydown'].forEach((eventName) => {
    window.addEventListener(eventName, unlockAudio, { once: true, passive: true });
  });

  window.setTimeout(showLeadAlert, 6000);
  window.setInterval(showLeadAlert, 45000);
}
