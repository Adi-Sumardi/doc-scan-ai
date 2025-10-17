import React, { useState, useEffect, useRef } from 'react';
import { Brain, Sparkles, Loader2, FileText, FolderOpen, CheckCircle } from 'lucide-react';

interface RealtimeOCRProcessingProps {
  batchId: string;
  onComplete?: () => void;
  className?: string;
}

interface Particle {
  id: number;
  x: number;
  y: number;
  size: number;
  speedX: number;
  speedY: number;
  color: string;
  opacity: number;
}

const RealtimeOCRProcessing: React.FC<RealtimeOCRProcessingProps> = ({
  batchId,
  onComplete,
  className = ''
}) => {
  const [showConfetti, setShowConfetti] = useState(false);
  const [particles, setParticles] = useState<Particle[]>([]);
  const [scanProgress, setScanProgress] = useState(0);
  const [statusText, setStatusText] = useState('Initializing AI Scanner...');
  const [isFadingOut, setIsFadingOut] = useState(false);
  const canvasRef = useRef<HTMLDivElement>(null);
  const animationTimerRef = useRef<NodeJS.Timeout | null>(null);
  const completeTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);
  const hasStartedRef = useRef(false); // Prevent restart after completion
  const currentBatchIdRef = useRef<string | null>(null); // Track current batch
  const lastProgressRef = useRef(0); // Track last progress to prevent regression
  const onCompleteRef = useRef(onComplete); // Save callback to ref to prevent re-renders

  // Keep onComplete ref updated
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  // Generate particles for visual effects
  useEffect(() => {
    const colors = ['#8B5CF6', '#3B82F6', '#10B981', '#F59E0B', '#EF4444'];
    const newParticles: Particle[] = Array.from({ length: 30 }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 4 + 2,
      speedX: (Math.random() - 0.5) * 0.5,
      speedY: (Math.random() - 0.5) * 0.5,
      color: colors[Math.floor(Math.random() * colors.length)],
      opacity: Math.random() * 0.3 + 0.2
    }));
    setParticles(newParticles);
  }, []);

  // Real-time polling animation with backend status check
  useEffect(() => {
    // Reset flag if batchId changed (new batch)
    if (currentBatchIdRef.current !== batchId) {
      console.log('🔄 New batch detected, resetting animation');
      hasStartedRef.current = false;
      currentBatchIdRef.current = batchId;
      lastProgressRef.current = 0; // Reset progress for new batch
      setScanProgress(0);
    }

    // IMPORTANT: Prevent animation from restarting ONLY if it's currently running
    // Check if timer exists - if it was cleared, we need to restart
    if (hasStartedRef.current && animationTimerRef.current !== null) {
      console.log('⏭️ Animation already running for this batch, skipping restart');
      return;
    }

    console.log('🎬 Starting animation for batch:', batchId);
    hasStartedRef.current = true;
    isMountedRef.current = true;

    const statuses = [
      'Initializing AI Scanner...',
      'Connecting to processing server...',
      'Analyzing document structure...',
      'Extracting text with AI...',
      'Processing document data...',
      'Applying intelligent parsing...',
      'Optimizing results...',
      'Finalizing extraction...',
      'Almost complete...',
      'Processing Smart Mapper AI'
    ];

    const startTime = Date.now();
    lastProgressRef.current = 0; // Reset for new batch
    let hasCalledComplete = false; // Prevent multiple calls

    // ✅ FIX: Poll backend for REAL batch status
    const checkBatchStatus = async () => {
      try {
        // Get JWT token from localStorage
        const token = localStorage.getItem('token') || localStorage.getItem('access_token');

        const response = await fetch(`http://localhost:8000/api/batches/${batchId}`, {
          headers: {
            'Authorization': token ? `Bearer ${token}` : '',
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          console.error(`❌ Batch status check failed: ${response.status} ${response.statusText}`);
          return null;
        }

        const batch = await response.json();
        return batch;
      } catch (error) {
        console.error('Failed to check batch status:', error);
        return null;
      }
    };

    const progressInterval = setInterval(async () => {
      // Check real backend status
      const batch = await checkBatchStatus();

      if (batch && batch.status === 'completed' && !hasCalledComplete) {
        // ✅ Backend says processing is DONE!
        hasCalledComplete = true;
        console.log('✅ Backend processing complete, showing results');
        clearInterval(progressInterval);
        setScanProgress(100);
        setStatusText('Processing Complete! Loading results...');
        setShowConfetti(true);

        // Wait for confetti, then fade out smoothly
        completeTimeoutRef.current = setTimeout(() => {
          if (isMountedRef.current) {
            setShowConfetti(false);
            // Start fade out animation
            setIsFadingOut(true);

            // Call onComplete after fade animation
            setTimeout(() => {
              if (isMountedRef.current && onCompleteRef.current) {
                console.log('🔄 Executing onComplete callback');
                onCompleteRef.current();
              }
            }, 600); // Match fade-out duration
          }
        }, 1500);
        return;
      }

      // Natural milestone-based progress
      const elapsed = (Date.now() - startTime) / 1000; // Convert to seconds

      // Define milestones: [seconds, progress%]
      const milestones = [
        [0, 0],     // Start
        [1, 19],    // 1 second → 19%
        [5, 25],    // 5 seconds → 25%
        [8, 55],    // 8 seconds → 55%
        [10, 85],   // 10 seconds → 85%
        [15, 95],   // 15+ seconds → cap at 95% until backend confirms
      ];

      // Calculate progress based on milestones with smooth interpolation
      let targetProgress = 0;
      for (let i = 0; i < milestones.length - 1; i++) {
        const [time1, progress1] = milestones[i];
        const [time2, progress2] = milestones[i + 1];

        if (elapsed >= time1 && elapsed < time2) {
          // Interpolate between milestones
          const ratio = (elapsed - time1) / (time2 - time1);
          // Use ease-out curve for smooth deceleration
          const easedRatio = 1 - Math.pow(1 - ratio, 3);
          targetProgress = progress1 + (progress2 - progress1) * easedRatio;
          break;
        }
      }

      // Cap at last milestone if exceeded
      if (elapsed >= milestones[milestones.length - 1][0]) {
        targetProgress = milestones[milestones.length - 1][1];
      }

      // Smooth transition to target progress - ALWAYS move forward!
      const currentProgress = lastProgressRef.current;
      const diff = targetProgress - currentProgress;

      // Calculate smooth progress with lerp
      let smoothProgress = currentProgress + diff * 0.3;

      // CRITICAL: Ensure we NEVER go backward
      smoothProgress = Math.max(smoothProgress, currentProgress);

      // Also ensure we reach target eventually (snap when very close)
      if (Math.abs(targetProgress - smoothProgress) < 0.1) {
        smoothProgress = targetProgress;
      }

      // Debug logging
      console.log(`⏱️ ${elapsed.toFixed(1)}s | Current: ${currentProgress.toFixed(1)}% | Target: ${targetProgress.toFixed(1)}% | Smooth: ${smoothProgress.toFixed(1)}%`);

      // Only update if progress changed significantly
      if (Math.abs(smoothProgress - lastProgressRef.current) > 0.1) {
        setScanProgress(smoothProgress);
        lastProgressRef.current = smoothProgress;

        // Update status text based on progress
        const statusIndex = Math.min(
          Math.floor((smoothProgress / 95) * (statuses.length - 1)),
          statuses.length - 1
        );
        setStatusText(statuses[statusIndex]);
      }
    }, 500); // Poll every 0.5 seconds for smoother progress

    animationTimerRef.current = progressInterval;

    return () => {
      console.log('🧹 Cleaning up animation');
      isMountedRef.current = false;
      // Don't reset hasStartedRef here - let it persist across re-renders for same batch
      // hasStartedRef is only reset when batchId changes (see above)
      if (animationTimerRef.current) {
        clearInterval(animationTimerRef.current);
        animationTimerRef.current = null;
      }
      if (completeTimeoutRef.current) {
        clearTimeout(completeTimeoutRef.current);
        completeTimeoutRef.current = null;
      }
    };
  }, [batchId]); // Only depend on batchId - onComplete is stable via ref

  return (
    <div
      className={`bg-gradient-to-br from-gray-50 to-blue-50 rounded-lg p-8 shadow-xl border border-gray-200 relative overflow-hidden transition-all duration-600 ${className}`}
      style={{
        opacity: isFadingOut ? 0 : 1,
        transform: isFadingOut ? 'scale(0.95)' : 'scale(1)',
        transition: 'opacity 0.6s ease-out, transform 0.6s ease-out'
      }}
    >
      {/* Animated Background Particles - Enhanced with better movement */}
      <div ref={canvasRef} className="absolute inset-0 pointer-events-none overflow-hidden">
        {particles.map(particle => (
          <div
            key={particle.id}
            className="absolute rounded-full"
            style={{
              left: `${particle.x}%`,
              top: `${particle.y}%`,
              width: `${particle.size}px`,
              height: `${particle.size}px`,
              backgroundColor: particle.color,
              opacity: particle.opacity,
              boxShadow: `0 0 ${particle.size * 3}px ${particle.color}, 0 0 ${particle.size * 6}px ${particle.color}`,
              animation: `
                floatUpDown ${4 + particle.id * 0.3}s ease-in-out infinite,
                floatLeftRight ${5 + particle.id * 0.4}s ease-in-out infinite,
                pulseGlow ${2 + particle.id * 0.2}s ease-in-out infinite
              `,
              animationDelay: `${particle.id * 0.15}s`,
              filter: 'blur(1px)'
            }}
          />
        ))}
      </div>

      {/* Rotating Scanning Beam */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden opacity-30">
        <div
          className="absolute top-1/2 left-1/2 w-full h-1 origin-left"
          style={{
            background: 'linear-gradient(to right, transparent, rgba(59, 130, 246, 0.8), transparent)',
            transform: 'translateY(-50%)',
            animation: 'rotateScan 4s linear infinite',
            boxShadow: '0 0 20px rgba(59, 130, 246, 0.6)'
          }}
        />
      </div>

      {/* Confetti Effect */}
      {showConfetti && (
        <div className="absolute inset-0 pointer-events-none z-50">
          {Array.from({ length: 50 }).map((_, i) => (
            <div
              key={`confetti-${i}`}
              className="absolute w-2 h-2 rounded-full animate-confetti"
              style={{
                left: `${Math.random() * 100}%`,
                top: '-10px',
                backgroundColor: ['#8B5CF6', '#3B82F6', '#10B981', '#F59E0B', '#EF4444'][i % 5],
                animationDelay: `${Math.random() * 0.5}s`,
                animationDuration: `${Math.random() * 2 + 1}s`
              }}
            />
          ))}
        </div>
      )}

      {/* Scanning Wave Effect */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div 
          className="absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-blue-500 to-transparent opacity-50"
          style={{
            top: `${scanProgress}%`,
            transition: 'top 0.1s linear',
            boxShadow: '0 0 20px rgba(59, 130, 246, 0.8)'
          }}
        />
      </div>

      {/* Header with Enhanced Glow */}
      <div className="flex items-center justify-center space-x-3 mb-8 relative z-10">
        <div className="relative">
          {/* Glowing ring effect */}
          <div className="absolute inset-0 bg-gradient-to-r from-purple-500 to-blue-500 rounded-xl opacity-50 blur-xl animate-pulse" />
          <div
            className="relative w-16 h-16 bg-gradient-to-r from-purple-500 via-blue-500 to-purple-500 rounded-xl flex items-center justify-center shadow-2xl"
            style={{
              animation: 'gradientShift 3s ease-in-out infinite, floatUpDown 2s ease-in-out infinite'
            }}
          >
            <Brain className="w-8 h-8 text-white" style={{ animation: 'pulse 2s ease-in-out infinite' }} />
          </div>
        </div>
        <div className="text-center">
          <h3 className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent mb-1"
              style={{ animation: 'fadeInUp 0.6s ease-out' }}>
            AI Document Scanner
          </h3>
          <p className="text-sm text-gray-600 flex items-center gap-2 justify-center">
            <Sparkles className="w-4 h-4 text-yellow-500" style={{ animation: 'twinkle 1.5s ease-in-out infinite' }} />
            <span style={{ animation: 'fadeInUp 0.6s ease-out 0.2s both' }}>Powered by Advanced AI</span>
            <Sparkles className="w-4 h-4 text-yellow-500" style={{ animation: 'twinkle 1.5s ease-in-out infinite 0.5s' }} />
          </p>
        </div>
      </div>

      {/* Circular Progress Indicator OR Document Organizing Animation */}
      <div className="flex justify-center mb-8 relative z-10">
        {scanProgress >= 100 ? (
          /* Document Organizing Animation at 100% */
          <div className="relative flex flex-col items-center justify-center h-48">
            {/* Animated folder container */}
            <div className="relative w-32 h-32 mb-4">
              {/* Folder */}
              <div className="absolute inset-0 flex items-center justify-center">
                <FolderOpen className="w-24 h-24 text-blue-500 animate-pulse" />
              </div>

              {/* Flying documents into folder */}
              {[0, 1, 2, 3, 4].map((i) => (
                <div
                  key={`doc-${i}`}
                  className="absolute"
                  style={{
                    animation: `flyIntoFolder 1.5s ease-in-out infinite`,
                    animationDelay: `${i * 0.3}s`,
                    left: `${-20 + i * 10}px`,
                    top: `-${30 + i * 5}px`,
                  }}
                >
                  <FileText className="w-8 h-8 text-purple-500" />
                </div>
              ))}

              {/* Check mark appears */}
              <div
                className="absolute top-0 right-0"
                style={{
                  animation: 'popIn 0.5s ease-out 1.5s both'
                }}
              >
                <div className="bg-green-500 rounded-full p-1">
                  <CheckCircle className="w-6 h-6 text-white" />
                </div>
              </div>
            </div>

            {/* Organizing text */}
            <div className="text-center">
              <p className="text-lg font-semibold text-gray-700 animate-pulse">
                Organizing documents...
              </p>
              <p className="text-sm text-gray-500 mt-1">
                Preparing your results
              </p>
            </div>
          </div>
        ) : (
          /* Enhanced Circular Progress with Ripple Effect */
          <div className="relative inline-flex items-center justify-center">
            {/* Ripple rings */}
            <div className="absolute w-48 h-48 rounded-full border-2 border-purple-300 opacity-20" style={{ animation: 'ripple 2s ease-out infinite' }} />
            <div className="absolute w-48 h-48 rounded-full border-2 border-blue-300 opacity-20" style={{ animation: 'ripple 2s ease-out infinite 0.5s' }} />
            <div className="absolute w-48 h-48 rounded-full border-2 border-green-300 opacity-20" style={{ animation: 'ripple 2s ease-out infinite 1s' }} />

            <svg className="w-48 h-48 transform -rotate-90" style={{ filter: 'drop-shadow(0 0 8px rgba(139, 92, 246, 0.3))' }}>
              {/* Background circle with glow */}
              <circle
                cx="96"
                cy="96"
                r="88"
                stroke="#E5E7EB"
                strokeWidth="10"
                fill="none"
                opacity="0.3"
              />
              {/* Animated progress circle with smooth easing */}
              <circle
                cx="96"
                cy="96"
                r="88"
                stroke="url(#gradient)"
                strokeWidth="10"
                fill="none"
                strokeDasharray={`${2 * Math.PI * 88}`}
                strokeDashoffset={`${2 * Math.PI * 88 * (1 - scanProgress / 100)}`}
                style={{
                  transition: 'stroke-dashoffset 0.5s cubic-bezier(0.4, 0, 0.2, 1)',
                  filter: 'drop-shadow(0 0 4px currentColor)'
                }}
                strokeLinecap="round"
              />
              {/* Gradient with animated colors */}
              <defs>
                <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#8B5CF6">
                    <animate attributeName="stop-color" values="#8B5CF6; #A78BFA; #8B5CF6" dur="3s" repeatCount="indefinite" />
                  </stop>
                  <stop offset="50%" stopColor="#3B82F6">
                    <animate attributeName="stop-color" values="#3B82F6; #60A5FA; #3B82F6" dur="3s" repeatCount="indefinite" />
                  </stop>
                  <stop offset="100%" stopColor="#10B981">
                    <animate attributeName="stop-color" values="#10B981; #34D399; #10B981" dur="3s" repeatCount="indefinite" />
                  </stop>
                </linearGradient>
              </defs>
            </svg>

            {/* Center content with breathing animation */}
            <div className="absolute flex flex-col items-center">
              <div
                className="text-6xl font-bold text-gray-800"
                style={{
                  animation: 'fadeInUp 0.8s ease-out',
                  textShadow: '0 2px 8px rgba(139, 92, 246, 0.3), 0 4px 16px rgba(59, 130, 246, 0.2)',
                  letterSpacing: '-0.02em'
                }}
              >
                {Math.round(scanProgress)}%
              </div>
              <Loader2 className="w-6 h-6 text-blue-500 mt-2" style={{ animation: 'spin 1s linear infinite' }} />
            </div>
          </div>
        )}
      </div>

      {/* Status Text with Smooth Transitions */}
      <div className="text-center mb-4 relative z-10">
        <p className="text-lg font-medium text-gray-800 mb-1"
           style={{
             animation: 'fadeInUp 0.5s ease-out',
             textShadow: '0 2px 4px rgba(0,0,0,0.1)'
           }}>
          {statusText}
        </p>
        <p className="text-sm text-blue-600 mt-2 flex items-center justify-center gap-2"
           style={{ animation: 'fadeInUp 0.6s ease-out 0.2s both' }}>
          <span className="inline-block w-2 h-2 bg-blue-500 rounded-full" style={{ animation: 'pulseGlow 1.5s ease-in-out infinite' }} />
          Processing your documents with AI
          <span className="inline-block w-2 h-2 bg-blue-500 rounded-full" style={{ animation: 'pulseGlow 1.5s ease-in-out infinite 0.5s' }} />
        </p>
      </div>

      {/* Enhanced Progress Bar */}
      <div className="relative z-10 px-4 mb-4">
        <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden shadow-inner relative">
          <div
            className="bg-gradient-to-r from-purple-500 via-blue-500 to-green-500 h-4 rounded-full transition-all duration-300 relative overflow-hidden"
            style={{ width: `${scanProgress}%` }}
          >
            {/* Shimmer effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-30 animate-shimmer" style={{ backgroundSize: '200% 100%' }} />
            {/* Glowing edge */}
            <div className="absolute right-0 top-0 bottom-0 w-2 bg-white opacity-70 blur-sm" />
          </div>
        </div>
        <div className="flex justify-center mt-1 text-xs text-gray-600">
          <span>{Math.round(scanProgress)}% Complete</span>
        </div>
      </div>

      {/* Floating sparkles around the progress */}
      <div className="absolute inset-0 pointer-events-none z-20">
        {[...Array(6)].map((_, i) => (
          <Sparkles 
            key={i}
            className="absolute w-5 h-5 text-yellow-400 animate-pulse" 
            style={{
              left: `${15 + i * 15}%`,
              top: `${50 + Math.sin(i) * 20}%`,
              animationDelay: `${i * 0.3}s`,
              opacity: scanProgress > i * 15 ? 1 : 0.2
            }}
          />
        ))}
      </div>
    </div>
  );
};

export default RealtimeOCRProcessing;
