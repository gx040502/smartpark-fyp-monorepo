'use client';

import { useState, useRef, MouseEvent } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { apiFetch } from '@/lib/api';
import { AlertCircle, CheckCircle2, Upload, Crosshair } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

interface Point {
  x: number;
  y: number;
}

export default function LiveCameraSimulation() {
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [points, setPoints] = useState<Point[]>([]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle');
  const [hasCongestion, setHasCongestion] = useState(false); // To test the webhook UI reaction
  const svgRef = useRef<SVGSVGElement>(null);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setVideoSrc(url);
      setPoints([]);
      setSaveStatus('idle');
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
        setIsDrawing(false);
      }
    }
  };

  const saveRoi = async () => {
    if (points.length !== 4) return;
    
    setSaveStatus('saving');
    try {
      const res = await apiFetch('/roi/coordinates', {
        method: 'POST',
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

  // Mock a webhook trigger for demonstration purposes
  const simulateCongestion = () => {
    setHasCongestion(true);
    setTimeout(() => setHasCongestion(false), 5000); // clear after 5s
  };

  return (
    <Card className="col-span-1 md:col-span-3">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl font-bold flex items-center gap-2">
            <Crosshair className="h-5 w-5" /> Live Exit Camera & ROI Configuration
          </CardTitle>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={simulateCongestion} className="text-xs">
              MOCK: Trigger Congestion Alert
            </Button>
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
        {hasCongestion && (
          <Alert variant="destructive" className="mb-4 animate-in slide-in-from-top-2">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Traffic Congestion Alert!</AlertTitle>
            <AlertDescription>
              Python Microservice has detected a vehicle dwelling in the ROI for too long.
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
                      {saveStatus === 'saving' ? 'Saving...' : saveStatus === 'success' ? 'Saved' : 'Save ROI'}
                    </Button>
                  </div>
                  
                  {saveStatus === 'success' && (
                    <p className="text-xs text-green-600 text-center">Coordinates sent to Python API!</p>
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
