'use client';

import { useState, useRef, MouseEvent, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertCircle, CheckCircle2, Upload, Crosshair, Loader2 } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

// Python traffic congestion backend URL
const TRAFFIC_API_URL = 'http://127.0.0.1:8002';

interface Point {
  x: number;
  y: number;
}

// Helper to sort 4 points in a clockwise order so the polygon never crosses itself
function sortPointsClockwise(points: Point[]): Point[] {
  if (points.length < 3) return points;

  // Find the centroid (center point)
  const cx = points.reduce((sum, p) => sum + p.x, 0) / points.length;
  const cy = points.reduce((sum, p) => sum + p.y, 0) / points.length;

  // Sort by angle from the centroid
  return [...points].sort((a, b) => {
    const angleA = Math.atan2(a.y - cy, a.x - cx);
    const angleB = Math.atan2(b.y - cy, b.x - cx);
    return angleA - angleB;
  });
}

export default function LiveCameraSimulation() {
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [points, setPoints] = useState<Point[]>([]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle'); // to track the progress of sending the video to python backend
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle'); //to track the progress of sending the 4 ROi points to Python backend
  const [hasCongestion, setHasCongestion] = useState(false);
  const svgRef = useRef<SVGSVGElement>(null);

  // trigger that tells the useEffect hook to start polling for traffic congestion from Python backend
  // trigger whenever saveStatus changes
  // only proceed to call ${TRAFFIC_API_URL}/congestion` when saveStatus is success every 1 second
  useEffect(() => {
    if (saveStatus !== 'success') return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${TRAFFIC_API_URL}/congestion`);
        if (res.ok) {
          const data = await res.json();
          setHasCongestion(data.is_congested);
        }
      } catch (e) {
        // Silently ignore polling errors
      }
    }, 1000); // Poll every 1 second

    return () => clearInterval(interval);
  }, [saveStatus]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Show local preview immediately
    const url = URL.createObjectURL(file);
    setVideoSrc(url);
    setPoints([]);
    setSaveStatus('idle');

    // Upload the video file to the Python backend
    setUploadStatus('uploading');
    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch(`${TRAFFIC_API_URL}/upload`, {
        method: 'POST',
        body: formData,
        // NOTE: Do NOT set Content-Type header. The browser sets it automatically
        // with the correct multipart/form-data boundary string.
      });

      if (res.ok) {
        setUploadStatus('success');
        // Auto-enable drawing mode after successful upload
        setIsDrawing(true);
      } else {
        setUploadStatus('error');
      }
    } catch {
      setUploadStatus('error');
    }
  };

  const handleSvgClick = (e: MouseEvent<SVGSVGElement>) => {
    if (!isDrawing) return;

    if (points.length >= 4) {
      setIsDrawing(false);
      return;
    }

    if (svgRef.current) {
      const rect = svgRef.current.getBoundingClientRect();
      // Calculate coordinates relative to the SVG size (0 to 100 percentage)
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;

      const newPoints = [...points, { x, y }];
      setPoints(newPoints);

      if (newPoints.length === 4) {
        setPoints(sortPointsClockwise(newPoints));
        setIsDrawing(false);
      }
    }
  };

  const saveRoi = async () => {
    if (points.length !== 4) return;

    setSaveStatus('saving');
    try {
      const res = await fetch(`${TRAFFIC_API_URL}/roi/coordinates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ points })
      });

      if (res.ok) {
        setSaveStatus('success');
      } else {
        setSaveStatus('error');
      }
    } catch {
      setSaveStatus('error');
    }
  };

  const clearRoi = () => {
    setPoints([]);
    setIsDrawing(true);
    setSaveStatus('idle');
  };

  return (
    <Card className="col-span-1 md:col-span-3">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl font-bold flex items-center gap-2">
            <Crosshair className="h-5 w-5" /> Live Exit Camera & ROI Configuration
          </CardTitle>
          <div className="flex gap-2">
            <div>
              <label htmlFor="video-upload" className="cursor-pointer inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-3">
                <Upload className="h-4 w-4 mr-2" /> Upload Video
              </label>
              <input id="video-upload" type="file" accept="video/*" className="hidden" onChange={handleFileUpload} />
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {saveStatus === 'success' && hasCongestion && (
          <Alert variant="destructive" className="mb-4 animate-in slide-in-from-top-2">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Traffic Congestion Alert!</AlertTitle>
            <AlertDescription>
              Vehicle dwelling in the ROI for too long.
            </AlertDescription>
          </Alert>
        )}

        {saveStatus === 'success' && !hasCongestion && (
          <Alert className="mb-4 animate-in slide-in-from-top-2 border-green-500 bg-green-50 text-green-900">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <AlertTitle className="text-green-800">Traffic Normal</AlertTitle>
            <AlertDescription className="text-green-700">
              No congestion detected in ROI.
            </AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="md:col-span-3 rounded-lg overflow-hidden border bg-muted relative aspect-video flex items-center justify-center">
            {!videoSrc ? (
              <div className="text-muted-foreground flex flex-col items-center">
                <Upload className="h-8 w-8 mb-2 opacity-50" />
                <p>Upload a video file to simulate camera feed</p>
              </div>
            ) : saveStatus === 'success' ? (
              /* After ROI is saved: show the MJPEG stream from Python (bounding boxes, ROI, HUD baked in) */
              <img
                src={`${TRAFFIC_API_URL}/video_feed`}
                className="w-full h-full object-cover"
                alt="Processed video feed with YOLO detections"
              />
            ) : (
              <>
                <video src={videoSrc} className="w-full h-full object-cover" autoPlay loop muted />

                {/* SVG Overlay for drawing ROI */}
                <svg
                  ref={svgRef}
                  className={`absolute inset-0 w-full h-full ${isDrawing ? 'cursor-crosshair' : 'cursor-default'}`}
                  onClick={handleSvgClick}
                >
                  {/* Draw polygon if we have points */}
                  {points.length > 0 && (
                    <polygon
                      points={points.map(p => `${p.x}%,${p.y}%`).join(' ')}
                      fill="rgba(239, 68, 68, 0.2)"
                      stroke="rgb(239, 68, 68)"
                      strokeWidth="2"
                    />
                  )}
                  {/* Draw points */}
                  {points.map((p, i) => (
                    <circle key={i} cx={`${p.x}%`} cy={`${p.y}%`} r="6" fill="white" stroke="red" strokeWidth="2" />
                  ))}
                </svg>
              </>
            )}
          </div>

          <div className="space-y-4">
            <div>
              <h3 className="font-medium mb-2">Region of Interest (ROI)</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Define the area where the Python AI agent should monitor for vehicles dwelling too long.
              </p>

              {!videoSrc ? (
                <Alert><AlertDescription>Please upload a video first.</AlertDescription></Alert>
              ) : uploadStatus === 'uploading' ? (
                <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-md p-3 text-sm flex gap-2 items-center">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="font-semibold">Uploading video to Python backend...</span>
                </div>
              ) : uploadStatus === 'error' ? (
                <div className="bg-red-50 border border-red-200 text-red-800 rounded-md p-3 text-sm flex gap-2 items-start">
                  <AlertCircle className="h-4 w-4 mt-0.5" />
                  <div>
                    <span className="font-semibold block mb-1">Upload Failed</span>
                    Make sure the Python backend is running on port 8002.
                    <code className="block mt-1 text-xs bg-red-100 px-2 py-1 rounded">uvicorn main:app --port 8002</code>
                  </div>
                </div>
              ) : points.length < 4 ? (
                <div className="bg-blue-50 border border-blue-200 text-blue-800 rounded-md p-3 text-sm flex gap-2 items-start">
                  <div className="mt-0.5"><AlertCircle className="h-4 w-4" /></div>
                  <div>
                    <span className="font-semibold block mb-1">Drawing mode active</span>
                    Click 4 points on the video feed to define a polygon.
                    <div className="mt-2 text-xs font-mono bg-blue-100 px-2 py-1 rounded inline-block">Points: {points.length}/4</div>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="bg-green-50 border border-green-200 text-green-800 rounded-md p-3 text-sm flex gap-2 items-center">
                    <CheckCircle2 className="h-4 w-4" />
                    <span className="font-semibold">ROI Defined</span>
                  </div>

                  <div className="flex gap-2 w-full">
                    <Button variant="outline" className="w-1/2" onClick={clearRoi}>Redraw</Button>
                    <Button
                      className="w-1/2"
                      onClick={saveRoi}
                      disabled={saveStatus === 'saving' || saveStatus === 'success'}
                    >
                      {saveStatus === 'saving' ? 'Saving...' : saveStatus === 'success' ? 'Saved ✓' : 'Save ROI & Start'}
                    </Button>
                  </div>

                  {saveStatus === 'success' && (
                    <p className="text-xs text-green-600 text-center">ROI sent! Check the Python terminal for the video window.</p>
                  )}
                  {saveStatus === 'error' && (
                    <p className="text-xs text-red-600 text-center">Failed to send ROI. Is the Python backend running?</p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
