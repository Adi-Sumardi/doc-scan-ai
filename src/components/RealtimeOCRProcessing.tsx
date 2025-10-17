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
  const canvasRef = useRef<HTMLDivElement>(null);
  const animationTimerRef = useRef<NodeJS.Timeout | null>(null);
  const completeTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);
  const hasStartedRef = useRef(false); // Prevent restart after completion
  const currentBatchIdRef = useRef<string | null>(null); // Track current batch

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
    let lastProgress = 0;
    let hasCalledComplete = false; // Prevent multiple calls

    // ✅ FIX: Poll backend for REAL batch status
    const checkBatchStatus = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/batches/${batchId}`);
        if (!response.ok) return null;
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

        completeTimeoutRef.current = setTimeout(() => {
          if (isMountedRef.current) {
            setShowConfetti(false);
            if (onComplete) {
              console.log('🔄 Executing onComplete callback');
              onComplete();
            }
          }
        }, 1500);
        return;
      }

      // Show smooth animation progress (not real progress, just visual)
      const elapsed = Date.now() - startTime;
      const rawProgress = Math.min(95, (elapsed / 10000) * 100); // Cap at 95% until backend confirms

      // Smooth easing function (ease-out)
      const progress = Math.min(95, rawProgress + (95 - rawProgress) * 0.1);

      // Only update if progress changed significantly
      if (Math.abs(progress - lastProgress) > 0.5) {
        setScanProgress(progress);
        lastProgress = progress;

        // Update status text based on progress
        const statusIndex = Math.min(
          Math.floor((progress / 95) * (statuses.length - 1)),
          statuses.length - 1
        );
        setStatusText(statuses[statusIndex]);
      }
    }, 1000); // Poll every 1 second

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
  }, [batchId, onComplete]); // Dependency: batchId and onComplete - animation restarts when batch changes

  return (
    <div className={`bg-white rounded-lg p-8 shadow-sm border relative overflow-hidden ${className}`}>
      {/* Animated Background Particles - Using CSS animations for better performance */}
      <div ref={canvasRef} className="absolute inset-0 pointer-events-none overflow-hidden">
        {particles.map(particle => (
          <div
            key={particle.id}
            className="absolute rounded-full animate-pulse"
            style={{
              left: `${particle.x}%`,
              top: `${particle.y}%`,
              width: `${particle.size}px`,
              height: `${particle.size}px`,
              backgroundColor: particle.color,
              opacity: particle.opacity,
              boxShadow: `0 0 ${particle.size * 2}px ${particle.color}`,
              animation: `float ${3 + particle.id * 0.5}s ease-in-out infinite, pulse ${2 + particle.id * 0.3}s ease-in-out infinite`,
              animationDelay: `${particle.id * 0.1}s`
            }}
          />
        ))}
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

      {/* Header */}
      <div className="flex items-center justify-center space-x-3 mb-8 relative z-10">
        <div className="w-16 h-16 bg-gradient-to-r from-purple-500 to-blue-500 rounded-xl flex items-center justify-center animate-pulse-slow shadow-xl">
          <Brain className="w-8 h-8 text-white" />
        </div>
        <div className="text-center">
          <h3 className="text-2xl font-bold text-gray-900 mb-1">AI Document Scanner</h3>
          <p className="text-sm text-gray-600 flex items-center gap-2 justify-center">
            <Sparkles className="w-4 h-4 text-yellow-500 animate-pulse" />
            Powered by Advanced AI
            <Sparkles className="w-4 h-4 text-yellow-500 animate-pulse" />
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
          /* Original Circular Progress */
          <div className="relative inline-flex items-center justify-center">
            <svg className="w-48 h-48 transform -rotate-90">
              <circle
                cx="96"
                cy="96"
                r="88"
                stroke="#E5E7EB"
                strokeWidth="8"
                fill="none"
              />
              <circle
                cx="96"
                cy="96"
                r="88"
                stroke="url(#gradient)"
                strokeWidth="8"
                fill="none"
                strokeDasharray={`${2 * Math.PI * 88}`}
                strokeDashoffset={`${2 * Math.PI * 88 * (1 - scanProgress / 100)}`}
                className="transition-all duration-300"
                strokeLinecap="round"
              />
              <defs>
                <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#8B5CF6" />
                  <stop offset="50%" stopColor="#3B82F6" />
                  <stop offset="100%" stopColor="#10B981" />
                </linearGradient>
              </defs>
            </svg>
            <div className="absolute flex flex-col items-center">
              <div className="text-5xl font-bold bg-gradient-to-r from-purple-600 via-blue-600 to-green-600 bg-clip-text text-transparent">
                {Math.round(scanProgress)}%
              </div>
              <Loader2 className="w-6 h-6 text-blue-500 animate-spin mt-2" />
            </div>
          </div>
        )}
      </div>

      {/* Status Text */}
      <div className="text-center mb-4 relative z-10">
        <p className="text-lg font-medium text-gray-700 animate-pulse">
          {statusText}
        </p>
        <p className="text-sm text-blue-600 mt-2">
          Processing your documents with AI...
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
