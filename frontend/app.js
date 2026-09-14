const revealItems = [...document.querySelectorAll('[data-reveal]')];

if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.16, rootMargin: '0px 0px -8% 0px' });

  revealItems.forEach(item => observer.observe(item));
} else {
  revealItems.forEach(item => item.classList.add('is-visible'));
}

const hero = document.querySelector('.landing-hero');

if (hero) {
  const reducedMotion = typeof window.matchMedia === 'function'
    ? window.matchMedia('(prefers-reduced-motion: reduce)')
    : { matches: false, addEventListener() {}, removeEventListener() {} };
  let nativeHeroInitialized = false;

  const initializeNativeHero = () => {
    if (nativeHeroInitialized) return;
    nativeHeroInitialized = true;

  const compactMotion = typeof window.matchMedia === 'function'
    && window.matchMedia('(max-width: 700px)').matches;
  const motionPlan = compactMotion ? {
    total: 6500,
    report: { delay: 0, duration: 800 },
    backSheets: [{ delay: 70, duration: 950 }, { delay: 40, duration: 880 }],
    entryNode: { delay: 520, duration: 560 },
    journeyIncoming: { delay: 700, duration: 3500 },
    reportSections: { delay: 260, stagger: 170, duration: 560 },
    scan: { delay: 420, duration: 1250 },
    protect: { delay: 1950, duration: 620 },
    extract: { delay: 2180, duration: 650 },
    incomingStreams: [
      { delay: 700, duration: 1400 },
      { delay: 900, duration: 1400 },
    ],
    evidenceTokens: [
      { delay: 700, duration: 3300, centerOffset: 0.56 },
      { delay: 900, duration: 3100, centerOffset: 0.53 },
    ],
    identityToken: { delay: 900, duration: 1650 },
    governance: { delay: 2000, duration: 650 },
    outgoingStreams: [
      { delay: 2700, duration: 1400 },
      { delay: 2900, duration: 1300 },
    ],
    outcomeSurface: { delay: 3650, duration: 1050 },
    outcomeTitle: { delay: 3850, duration: 600 },
    outcomeRows: [
      { delay: 4150, duration: 600 },
      { delay: 4400, duration: 600 },
    ],
    relationship: { delay: 4650, duration: 600 },
    analyticsBaseline: { delay: 4800, duration: 500 },
    analyticsBars: { delay: 4950, stagger: 100, duration: 450 },
    journeyOutcome: { delay: 4200, duration: 1150 },
    indicatorBand: { delay: 5350, duration: 500 },
    outcomeHalo: { delay: 5450, duration: 550 },
    indicator: { delay: 5600, duration: 600 },
    settle: { delay: 6100, duration: 400 },
  } : {
    total: 7200,
    report: { delay: 0, duration: 900 },
    backSheets: [{ delay: 90, duration: 1050 }, { delay: 50, duration: 980 }],
    entryNode: { delay: 650, duration: 650 },
    journeyIncoming: { delay: 750, duration: 3900 },
    reportSections: { delay: 300, stagger: 200, duration: 650 },
    scan: { delay: 500, duration: 1500 },
    protect: { delay: 2300, duration: 700 },
    extract: { delay: 2500, duration: 750 },
    incomingStreams: [
      { delay: 800, duration: 1600 },
      { delay: 1000, duration: 1500 },
      { delay: 1200, duration: 1400 },
    ],
    evidenceTokens: [
      { delay: 800, duration: 3800, centerOffset: 0.55 },
      { delay: 1000, duration: 3650, centerOffset: 0.52 },
      { delay: 1200, duration: 3450, centerOffset: 0.49 },
    ],
    identityToken: { delay: 1050, duration: 1800 },
    governance: { delay: 2150, duration: 750 },
    outgoingStreams: [
      { delay: 2900, duration: 1750 },
      { delay: 3080, duration: 1570 },
      { delay: 3260, duration: 1390 },
    ],
    outcomeSurface: { delay: 4150, duration: 1500 },
    outcomeTitle: { delay: 4350, duration: 700 },
    outcomeRows: [
      { delay: 4550, duration: 650 },
      { delay: 4750, duration: 650 },
      { delay: 4950, duration: 650 },
    ],
    relationship: { delay: 5100, duration: 700 },
    analyticsBaseline: { delay: 5250, duration: 600 },
    analyticsBars: { delay: 5350, stagger: 75, duration: 550 },
    journeyOutcome: { delay: 4650, duration: 1000 },
    indicatorBand: { delay: 5650, duration: 600 },
    outcomeHalo: { delay: 6000, duration: 550 },
    indicator: { delay: 6200, duration: 500 },
    settle: { delay: 6700, duration: 500 },
  };
  const origin = hero.querySelector('.hero-origin-motion');
  const backSheets = [...hero.querySelectorAll('.hero-back-sheet-motion')];
  const entryNode = hero.querySelector('.hero-pathway-entry-node');
  const journeyUnderlay = hero.querySelector('.hero-journey-underlay');
  const journeyPath = hero.querySelector('.hero-journey-path');
  const journeyForegroundUnderlay = hero.querySelector('.hero-journey-foreground-underlay');
  const journeyForeground = hero.querySelector('.hero-journey-foreground');
  const reportSections = [...hero.querySelectorAll('.hero-report-section')];
  const protectLayer = hero.querySelector('.hero-protect-layer');
  const extractLayer = hero.querySelector('.hero-extract-layer');
  const scanLayer = hero.querySelector('.hero-scan-layer');
  const allIncomingStreams = [...hero.querySelectorAll('.hero-evidence-stream-incoming')];
  const allOutgoingStreams = [...hero.querySelectorAll('.hero-evidence-stream-outgoing')];
  const incomingStreams = compactMotion ? allIncomingStreams.slice(0, 2) : allIncomingStreams;
  const outgoingStreams = compactMotion ? allOutgoingStreams.slice(0, 2) : allOutgoingStreams;
  const allStreams = [...allIncomingStreams, ...allOutgoingStreams];
  const governanceCore = hero.querySelector('.hero-governance-core');
  const allTokens = [...hero.querySelectorAll('.hero-evidence-token')];
  const tokens = compactMotion ? allTokens.slice(0, 2) : allTokens;
  const identityToken = hero.querySelector('.hero-identity-token');
  const outcome = hero.querySelector('.hero-outcome-motion');
  const outcomeSurface = hero.querySelector('.hero-outcome-surface');
  const outcomeTitle = hero.querySelector('.hero-outcome-title-area');
  const normalizedRows = [...hero.querySelectorAll('.hero-normalized-row')];
  const relationship = hero.querySelector('.hero-relationship-layer');
  const analyticsBaseline = hero.querySelector('.hero-analytics-layer path');
  const allAnalyticBars = [...hero.querySelectorAll('.hero-analytics-layer rect')];
  const analyticBars = compactMotion ? allAnalyticBars.slice(0, 3) : allAnalyticBars;
  const indicatorBand = hero.querySelector('.hero-indicator-band');
  const outcomeHalo = hero.querySelector('.hero-outcome-halo');
  const indicator = hero.querySelector('.hero-outcome-indicator');
  const sceneCaption = hero.querySelector('.hero-scene-caption');
  const pathLengths = new Map();
  const animations = [];
  const ease = 'cubic-bezier(.22,1,.36,1)';
  const pathEase = 'cubic-bezier(.4,0,.2,1)';
  const fadeEase = 'ease-out';
  let heroObserver = null;
  let heroIsVisible = !('IntersectionObserver' in window);
  let entrancePrepared = false;
  let initialFramePainted = false;
  let entranceStarted = false;
  let entranceComplete = false;
  let firstFrameRequest = null;
  let secondFrameRequest = null;
  let completionFrameRequest = null;
  let masterStart = null;

  const allAnimatedElements = [
    origin,
    ...backSheets,
    entryNode,
    journeyUnderlay,
    journeyPath,
    journeyForegroundUnderlay,
    journeyForeground,
    ...reportSections,
    protectLayer,
    extractLayer,
    scanLayer,
    ...allStreams,
    governanceCore,
    ...allTokens,
    identityToken,
    outcome,
    outcomeSurface,
    outcomeTitle,
    ...normalizedRows,
    relationship,
    analyticsBaseline,
    ...allAnalyticBars,
    indicatorBand,
    outcomeHalo,
    indicator,
    sceneCaption,
  ].filter(Boolean);

  const timing = (track, easing = ease) => ({
    duration: track.duration,
    delay: track.delay,
    easing,
  });

  const setTransformOrigin = (element, transformOrigin = 'center') => {
    if (!element) return;
    element.style.transformBox = 'fill-box';
    element.style.transformOrigin = transformOrigin;
  };

  const clearInlineMotionStyles = () => {
    const properties = [
      'opacity',
      'transform',
      'transform-box',
      'transform-origin',
      'stroke-dasharray',
      'stroke-dashoffset',
    ];
    allAnimatedElements.forEach(element => {
      properties.forEach(property => element.style.removeProperty(property));
    });
  };

  const applyFinalInlineState = () => {
    if (origin) {
      origin.style.opacity = '1';
      origin.style.transform = 'translate(0px, 0px) scale(1) rotate(0deg)';
    }
    backSheets.forEach(sheet => { sheet.style.transform = 'translate(0px, 0px)'; });
    if (entryNode) {
      entryNode.style.opacity = '1';
      entryNode.style.transform = 'scale(1)';
    }
    for (const path of [journeyUnderlay, journeyPath, journeyForegroundUnderlay, journeyForeground, ...allStreams]) {
      if (!path) continue;
      path.style.strokeDasharray = String(pathLengths.get(path) || path.getTotalLength());
      path.style.strokeDashoffset = '0';
      path.style.opacity = path === journeyUnderlay || path === journeyForegroundUnderlay ? '0.88' : '1';
    }
    reportSections.forEach(section => {
      section.style.opacity = '1';
      section.style.transform = 'translateX(0px)';
    });
    if (protectLayer) {
      protectLayer.style.opacity = '1';
      protectLayer.style.transform = 'scale(1)';
    }
    if (extractLayer) {
      extractLayer.style.opacity = '1';
      extractLayer.style.transform = 'translateY(0px)';
    }
    if (scanLayer) {
      scanLayer.style.opacity = '0';
      scanLayer.style.transform = 'translateY(330px)';
    }
    if (governanceCore) {
      governanceCore.style.opacity = '1';
      governanceCore.style.transform = 'scale(1)';
    }
    allTokens.forEach(token => {
      token.style.opacity = '1';
      token.style.transform = 'translate(0px, 0px) scale(1)';
    });
    if (identityToken) {
      identityToken.style.opacity = '1';
      identityToken.style.transform = 'translate(0px, 0px)';
    }
    if (outcomeSurface) {
      outcomeSurface.style.opacity = '1';
      outcomeSurface.style.transform = 'translateX(0px) scale(1)';
    }
    if (outcomeTitle) {
      outcomeTitle.style.opacity = '1';
      outcomeTitle.style.transform = 'translateX(0px)';
    }
    normalizedRows.forEach(row => {
      row.style.opacity = '1';
      row.style.transform = 'translateX(0px)';
    });
    if (relationship) {
      relationship.style.opacity = '1';
      relationship.style.transform = 'scale(1)';
    }
    if (analyticsBaseline) {
      analyticsBaseline.style.opacity = '1';
      analyticsBaseline.style.transform = 'scaleX(1)';
    }
    allAnalyticBars.forEach(bar => {
      bar.style.opacity = '1';
      bar.style.transform = 'scaleY(1)';
    });
    if (indicatorBand) {
      indicatorBand.style.opacity = '1';
      indicatorBand.style.transform = 'scaleX(1)';
    }
    if (outcomeHalo) {
      outcomeHalo.style.opacity = '1';
      outcomeHalo.style.transform = 'scale(1)';
    }
    if (indicator) {
      indicator.style.opacity = '1';
      indicator.style.transform = 'scale(1)';
    }
    if (sceneCaption) sceneCaption.style.opacity = '1';
  };

  const releaseLifecycle = () => {
    heroObserver?.disconnect();
    document.removeEventListener('visibilitychange', setPlaybackState);
    if ('removeEventListener' in reducedMotion) {
      reducedMotion.removeEventListener('change', handleMotionPreferenceChange);
    } else {
      reducedMotion.removeListener(handleMotionPreferenceChange);
    }
  };

  const finishEntrance = () => {
    if (entranceComplete) return;

    entranceComplete = true;
    if (firstFrameRequest !== null) window.cancelAnimationFrame(firstFrameRequest);
    if (secondFrameRequest !== null) window.cancelAnimationFrame(secondFrameRequest);
    animations.forEach(animation => animation.cancel());
    applyFinalInlineState();
    completionFrameRequest = window.requestAnimationFrame(() => {
      completionFrameRequest = null;
      clearInlineMotionStyles();
      hero.classList.remove('is-hero-motion-prepared', 'is-hero-motion-active');
      hero.classList.add('is-hero-motion-complete');
      document.documentElement.classList.remove('hero-motion-ready');
      releaseLifecycle();
    });
  };

  const addAnimation = (element, keyframes, options) => {
    if (!element) return null;
    const animation = element.animate(keyframes, { fill: 'both', ...options });
    if (masterStart !== null) animation.startTime = masterStart;
    animations.push(animation);
    return animation;
  };

  const startEntrance = () => {
    if (!entrancePrepared || entranceStarted || entranceComplete) return;

    entranceStarted = true;
    masterStart = document.timeline?.currentTime ?? performance.now();
    hero.classList.add('is-hero-motion-active');

    addAnimation(origin, [
      { opacity: 0.08, transform: 'translate(-34px, 46px) scale(.91) rotate(-1.2deg)' },
      { offset: 0.38, opacity: 0.68 },
      { opacity: 1, transform: 'translate(0px, 0px) scale(1) rotate(0deg)' },
    ], timing(motionPlan.report));

    backSheets.forEach((sheet, index) => {
      addAnimation(sheet, [
        { transform: index === 0 ? 'translate(-20px, 25px)' : 'translate(19px, 21px)' },
        { transform: 'translate(0px, 0px)' },
      ], timing(motionPlan.backSheets[index]));
    });

    addAnimation(entryNode, [
      { opacity: 0.15, transform: 'scale(.5)' },
      { opacity: 1, transform: 'scale(1)' },
    ], timing(motionPlan.entryNode));

    const journeyUnderlayLength = pathLengths.get(journeyUnderlay);
    addAnimation(journeyUnderlay, [
      { opacity: 0.12, strokeDashoffset: String(journeyUnderlayLength) },
      { opacity: 0.88, strokeDashoffset: '0' },
    ], timing(motionPlan.journeyIncoming, pathEase));

    const journeyLength = pathLengths.get(journeyPath);
    addAnimation(journeyPath, [
      { strokeDashoffset: String(journeyLength) },
      { strokeDashoffset: '0' },
    ], timing(motionPlan.journeyIncoming, pathEase));

    const journeyForegroundUnderlayLength = pathLengths.get(journeyForegroundUnderlay);
    addAnimation(journeyForegroundUnderlay, [
      { opacity: 0.12, strokeDashoffset: String(journeyForegroundUnderlayLength) },
      { opacity: 0.88, strokeDashoffset: '0' },
    ], timing(motionPlan.journeyOutcome, pathEase));

    const journeyForegroundLength = pathLengths.get(journeyForeground);
    addAnimation(journeyForeground, [
      { strokeDashoffset: String(journeyForegroundLength) },
      { strokeDashoffset: '0' },
    ], timing(motionPlan.journeyOutcome, pathEase));

    reportSections.forEach((section, index) => {
      addAnimation(section, [
        { opacity: 0.12, transform: 'translateX(20px)' },
        { opacity: 1, transform: 'translateX(0px)' },
      ], timing({
        delay: motionPlan.reportSections.delay + (index * motionPlan.reportSections.stagger),
        duration: motionPlan.reportSections.duration,
      }, fadeEase));
    });

    addAnimation(scanLayer, [
      { opacity: 0, transform: 'translateY(-42px)' },
      { offset: 0.14, opacity: 0.8 },
      { offset: 0.8, opacity: 0.4 },
      { opacity: 0, transform: 'translateY(330px)' },
    ], timing(motionPlan.scan, pathEase));

    addAnimation(protectLayer, [
      { opacity: 0, transform: 'scale(.9)' },
      { offset: 0.66, opacity: 0.92, transform: 'scale(.98)' },
      { opacity: 1, transform: 'scale(1)' },
    ], timing(motionPlan.protect));

    addAnimation(extractLayer, [
      { opacity: 0, transform: 'translateY(14px)' },
      { opacity: 1, transform: 'translateY(0px)' },
    ], timing(motionPlan.extract));

    incomingStreams.forEach((stream, index) => {
      const length = pathLengths.get(stream);
      const track = motionPlan.incomingStreams[index];
      addAnimation(stream, [
        { opacity: 0.15, strokeDashoffset: String(length) },
        { offset: 0.18, opacity: 0.88 },
        { opacity: 1, strokeDashoffset: '0' },
      ], timing(track, pathEase));
    });

    outgoingStreams.forEach((stream, index) => {
      const length = pathLengths.get(stream);
      const track = motionPlan.outgoingStreams[index];
      addAnimation(stream, [
        { opacity: 0.15, strokeDashoffset: String(length) },
        { offset: 0.18, opacity: 0.88 },
        { opacity: 1, strokeDashoffset: '0' },
      ], timing(track, pathEase));
    });

    const tokenOrigins = [
      'translate(-385px, 93px) scale(.82)',
      'translate(-370px, 105px) scale(.82)',
      'translate(-362px, 125px) scale(.82)',
    ];
    const tokenWaypoints = [
      'translate(-220px, 91px) scale(.92)',
      'translate(-212px, 69px) scale(.92)',
      'translate(-206px, 44px) scale(.92)',
    ];
    tokens.forEach((token, index) => {
      const track = motionPlan.evidenceTokens[index];
      addAnimation(token, [
        { opacity: 0, transform: tokenOrigins[index] },
        { offset: 0.12, opacity: 1, transform: tokenOrigins[index] },
        { offset: track.centerOffset, opacity: 1, transform: tokenWaypoints[index] },
        { opacity: 1, transform: 'translate(0px, 0px) scale(1)' },
      ], timing(track, pathEase));
    });

    addAnimation(identityToken, [
      { opacity: 0, transform: 'translate(-145px, -238px) scale(.82)' },
      { offset: 0.2, opacity: 1 },
      { opacity: 1, transform: 'translate(0px, 0px) scale(1)' },
    ], timing(motionPlan.identityToken, pathEase));

    addAnimation(governanceCore, [
      { opacity: 0, transform: 'scale(.88)' },
      { offset: 0.55, opacity: 0.72, transform: 'scale(.96)' },
      { opacity: 1, transform: 'scale(1)' },
    ], timing(motionPlan.governance));

    addAnimation(outcomeSurface, [
      { opacity: 0, transform: 'translateX(28px) scale(.985)' },
      { offset: 0.52, opacity: 0.62, transform: 'translateX(11px) scale(.993)' },
      { opacity: 1, transform: 'translateX(0px) scale(1)' },
    ], timing(motionPlan.outcomeSurface));

    addAnimation(outcomeTitle, [
      { opacity: 0, transform: 'translateX(18px)' },
      { opacity: 1, transform: 'translateX(0px)' },
    ], timing(motionPlan.outcomeTitle, fadeEase));

    normalizedRows.forEach((row, index) => {
      if (compactMotion && index > 1) return;
      const track = motionPlan.outcomeRows[index];
      addAnimation(row, [
        { opacity: 0, transform: 'translateX(24px)' },
        { opacity: 1, transform: 'translateX(0px)' },
      ], timing(track, fadeEase));
    });

    addAnimation(relationship, [
      { opacity: 0, transform: 'scale(.72)' },
      { opacity: 1, transform: 'scale(1)' },
    ], timing(motionPlan.relationship));

    addAnimation(analyticsBaseline, [
      { opacity: 0, transform: 'scaleX(0)' },
      { opacity: 1, transform: 'scaleX(1)' },
    ], timing(motionPlan.analyticsBaseline, pathEase));

    analyticBars.forEach((bar, index) => {
      addAnimation(bar, [
        { opacity: 0, transform: 'scaleY(0)' },
        { opacity: 1, transform: 'scaleY(1)' },
      ], timing({
        delay: motionPlan.analyticsBars.delay + (index * motionPlan.analyticsBars.stagger),
        duration: motionPlan.analyticsBars.duration,
      }));
    });

    addAnimation(indicatorBand, [
      { opacity: 0, transform: 'scaleX(.92)' },
      { opacity: 1, transform: 'scaleX(1)' },
    ], timing(motionPlan.indicatorBand, fadeEase));

    addAnimation(outcomeHalo, [
      { opacity: 0, transform: 'scale(.72)' },
      { offset: 0.7, opacity: 0.72, transform: 'scale(.96)' },
      { opacity: 1, transform: 'scale(1)' },
    ], timing(motionPlan.outcomeHalo, fadeEase));

    addAnimation(indicator, [
      { opacity: 0, transform: 'scale(.82)' },
      { offset: 0.68, opacity: 0.84, transform: 'scale(.97)' },
      { opacity: 1, transform: 'scale(1)' },
    ], timing(motionPlan.indicator));

    addAnimation(sceneCaption, [
      { opacity: 0.25 },
      { opacity: 1 },
    ], timing(motionPlan.settle, fadeEase));

    Promise.all(animations.map(animation => animation.finished.catch(() => null))).then(() => {
      if (!entranceComplete) finishEntrance();
    });
  };

  const prepareEntrance = () => {
    if (entrancePrepared || entranceComplete || reducedMotion.matches) return;

    if (
      !origin
      || typeof origin.animate !== 'function'
      || !journeyPath
      || !journeyForeground
      || !outcome
      || !outcomeSurface
      || !outcomeTitle
      || !analyticsBaseline
      || !indicatorBand
      || !indicator
    ) {
      entranceComplete = true;
      document.documentElement.classList.remove('hero-motion-ready');
      hero.classList.add('is-hero-motion-complete');
      releaseLifecycle();
      return;
    }

    setTransformOrigin(origin);
    origin.style.opacity = '0.08';
    origin.style.transform = 'translate(-34px, 46px) scale(.91) rotate(-1.2deg)';
    backSheets.forEach((sheet, index) => {
      setTransformOrigin(sheet);
      sheet.style.transform = index === 0 ? 'translate(-20px, 25px)' : 'translate(19px, 21px)';
    });
    setTransformOrigin(entryNode);
    if (entryNode) {
      entryNode.style.opacity = '0.15';
      entryNode.style.transform = 'scale(.5)';
    }

    for (const path of [journeyUnderlay, journeyPath, journeyForegroundUnderlay, journeyForeground, ...allStreams]) {
      const length = path.getTotalLength();
      pathLengths.set(path, length);
      path.style.strokeDasharray = String(length);
      path.style.strokeDashoffset = String(length);
      path.style.opacity = allStreams.includes(path)
        ? '0.15'
        : path === journeyUnderlay || path === journeyForegroundUnderlay ? '0.12' : '1';
    }

    reportSections.forEach(section => {
      setTransformOrigin(section);
      section.style.opacity = '0.12';
      section.style.transform = 'translateX(20px)';
    });
    setTransformOrigin(protectLayer);
    if (protectLayer) {
      protectLayer.style.opacity = '0';
      protectLayer.style.transform = 'scale(.9)';
    }
    setTransformOrigin(extractLayer);
    if (extractLayer) {
      extractLayer.style.opacity = '0';
      extractLayer.style.transform = 'translateY(14px)';
    }
    if (scanLayer) {
      scanLayer.style.opacity = '0';
      scanLayer.style.transform = 'translateY(-42px)';
    }

    setTransformOrigin(governanceCore);
    if (governanceCore) {
      governanceCore.style.opacity = '0';
      governanceCore.style.transform = 'scale(.88)';
    }
    const tokenOrigins = [
      'translate(-385px, 93px) scale(.82)',
      'translate(-370px, 105px) scale(.82)',
      'translate(-362px, 125px) scale(.82)',
    ];
    allTokens.forEach((token, index) => {
      setTransformOrigin(token);
      token.style.opacity = '0';
      token.style.transform = tokenOrigins[index];
    });
    setTransformOrigin(identityToken);
    if (identityToken) {
      identityToken.style.opacity = '0';
      identityToken.style.transform = 'translate(-145px, -238px) scale(.82)';
    }

    setTransformOrigin(outcomeSurface);
    if (outcomeSurface) {
      outcomeSurface.style.opacity = '0';
      outcomeSurface.style.transform = 'translateX(28px) scale(.985)';
    }
    setTransformOrigin(outcomeTitle);
    if (outcomeTitle) {
      outcomeTitle.style.opacity = '0';
      outcomeTitle.style.transform = 'translateX(18px)';
    }
    normalizedRows.forEach(row => {
      setTransformOrigin(row);
      row.style.opacity = '0';
      row.style.transform = 'translateX(24px)';
    });
    setTransformOrigin(relationship);
    if (relationship) {
      relationship.style.opacity = '0';
      relationship.style.transform = 'scale(.82)';
    }
    setTransformOrigin(analyticsBaseline, 'center left');
    if (analyticsBaseline) {
      analyticsBaseline.style.opacity = '0';
      analyticsBaseline.style.transform = 'scaleX(0)';
    }
    allAnalyticBars.forEach(bar => {
      setTransformOrigin(bar, 'center bottom');
      bar.style.opacity = '0';
      bar.style.transform = 'scaleY(0)';
    });
    setTransformOrigin(indicatorBand);
    if (indicatorBand) {
      indicatorBand.style.opacity = '0';
      indicatorBand.style.transform = 'scaleX(.92)';
    }
    setTransformOrigin(outcomeHalo);
    if (outcomeHalo) {
      outcomeHalo.style.opacity = '0';
      outcomeHalo.style.transform = 'scale(.72)';
    }
    setTransformOrigin(indicator);
    indicator.style.opacity = '0';
    indicator.style.transform = 'scale(.82)';
    if (sceneCaption) sceneCaption.style.opacity = '0.25';

    entrancePrepared = true;
    hero.classList.add('is-hero-motion-prepared');

    // Force all direct initial SVG states into layout before the one-time two-frame start.
    origin.getBoundingClientRect();
    firstFrameRequest = window.requestAnimationFrame(() => {
      firstFrameRequest = null;
      secondFrameRequest = window.requestAnimationFrame(() => {
        secondFrameRequest = null;
        initialFramePainted = true;
        setPlaybackState();
      });
    });
  };

  function setPlaybackState() {
    if (entranceComplete || reducedMotion.matches) return;

    const canPlay = !document.hidden && heroIsVisible;
    if (!entrancePrepared && canPlay) {
      prepareEntrance();
      return;
    }
    if (!initialFramePainted) return;
    if (!entranceStarted && canPlay) {
      startEntrance();
      return;
    }
    if (!entranceStarted) return;
    animations.forEach(animation => canPlay ? animation.play() : animation.pause());
  }

  function handleMotionPreferenceChange(event) {
    if (event.matches) {
      finishEntrance();
      return;
    }
    document.documentElement.classList.add('hero-motion-ready');
    setPlaybackState();
  }

  document.addEventListener('visibilitychange', setPlaybackState);
  if ('addEventListener' in reducedMotion) {
    reducedMotion.addEventListener('change', handleMotionPreferenceChange);
  } else {
    reducedMotion.addListener(handleMotionPreferenceChange);
  }

  if ('IntersectionObserver' in window) {
    const initialBounds = hero.getBoundingClientRect();
    heroIsVisible = initialBounds.bottom > 0 && initialBounds.top < window.innerHeight;
    heroObserver = new IntersectionObserver(entries => {
      const heroEntry = entries.find(entry => entry.target === hero);
      if (!heroEntry) return;
      heroIsVisible = heroEntry.isIntersecting && heroEntry.intersectionRatio >= 0.18;
      setPlaybackState();
    }, { threshold: 0.18 });
    heroObserver.observe(hero);
  }

  setPlaybackState();
  };

  const requestedRenderer = hero.dataset.heroRenderer === 'video' ? 'video' : 'native';
  const cinematicVideo = hero.querySelector('.hero-cinematic-video');
  let videoObserver = null;
  let videoFrameReady = false;
  let videoPlaybackReady = false;
  let videoCompleted = false;
  let videoInViewport = true;
  let videoFallbackActive = false;
  let videoPausedByLifecycle = false;

  const stopVideoLifecycle = () => {
    videoObserver?.disconnect();
    videoObserver = null;
    document.removeEventListener('visibilitychange', syncVideoPlayback);
    if ('removeEventListener' in reducedMotion) {
      reducedMotion.removeEventListener('change', handleVideoMotionPreferenceChange);
    } else {
      reducedMotion.removeListener(handleVideoMotionPreferenceChange);
    }
  };

  const activateNativeRenderer = ({ animate = true } = {}) => {
    if (videoFallbackActive) return;
    videoFallbackActive = true;
    cinematicVideo?.pause();
    stopVideoLifecycle();
    hero.classList.remove('is-video-ready', 'is-video-complete');
    hero.dataset.heroRenderer = 'native';

    if (animate && !reducedMotion.matches) {
      document.documentElement.classList.add('hero-motion-ready');
      initializeNativeHero();
      return;
    }

    document.documentElement.classList.remove('hero-motion-ready');
    hero.classList.add('is-hero-motion-complete');
  };

  const attemptVideoPlayback = () => {
    if (!cinematicVideo || videoCompleted || videoFallbackActive || reducedMotion.matches) return;
    const playAttempt = cinematicVideo.play();
    if (!playAttempt || typeof playAttempt.then !== 'function') {
      videoPlaybackReady = true;
      revealVideoWhenReady();
      return;
    }
    playAttempt.then(() => {
      videoPlaybackReady = true;
      videoPausedByLifecycle = false;
      revealVideoWhenReady();
    }).catch(() => activateNativeRenderer());
  };

  const syncVideoPlayback = () => {
    if (!cinematicVideo || videoCompleted || videoFallbackActive) return;
    const shouldPause = document.hidden || !videoInViewport;
    if (shouldPause) {
      if (!cinematicVideo.paused) {
        cinematicVideo.pause();
        videoPausedByLifecycle = true;
      }
      return;
    }
    if (videoPausedByLifecycle) attemptVideoPlayback();
  };

  const observeVideoLifecycle = () => {
    if (!('IntersectionObserver' in window) || videoObserver) return;
    videoObserver = new IntersectionObserver(entries => {
      const entry = entries.find(candidate => candidate.target === hero);
      if (!entry) return;
      videoInViewport = entry.isIntersecting && entry.intersectionRatio >= 0.16;
      syncVideoPlayback();
    }, { threshold: [0, 0.16] });
    videoObserver.observe(hero);
  };

  function revealVideoWhenReady() {
    if (!videoFrameReady || !videoPlaybackReady || videoFallbackActive || reducedMotion.matches) return;
    hero.classList.add('is-video-ready');
    document.documentElement.classList.remove('hero-motion-ready');
    observeVideoLifecycle();
  }

  function handleVideoMotionPreferenceChange(event) {
    if (event.matches) activateNativeRenderer({ animate: false });
  }

  const initializeVideoRenderer = () => {
    if (!cinematicVideo || typeof cinematicVideo.play !== 'function') {
      activateNativeRenderer();
      return;
    }

    cinematicVideo.autoplay = true;
    cinematicVideo.muted = true;
    cinematicVideo.playsInline = true;
    cinematicVideo.loop = false;
    cinematicVideo.controls = false;

    cinematicVideo.addEventListener('loadeddata', () => {
      videoFrameReady = true;
      revealVideoWhenReady();
    }, { once: true });
    cinematicVideo.addEventListener('ended', () => {
      videoCompleted = true;
      videoPausedByLifecycle = false;
      cinematicVideo.pause();
      hero.classList.add('is-video-complete');
    }, { once: true });
    cinematicVideo.addEventListener('error', () => activateNativeRenderer(), { once: true });
    document.addEventListener('visibilitychange', syncVideoPlayback);
    if ('addEventListener' in reducedMotion) {
      reducedMotion.addEventListener('change', handleVideoMotionPreferenceChange);
    } else {
      reducedMotion.addListener(handleVideoMotionPreferenceChange);
    }

    if (cinematicVideo.readyState >= 2) videoFrameReady = true;
    attemptVideoPlayback();
  };

  if (requestedRenderer === 'video' && !reducedMotion.matches) {
    initializeVideoRenderer();
  } else {
    activateNativeRenderer({ animate: !reducedMotion.matches });
  }
}
