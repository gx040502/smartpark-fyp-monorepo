'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, CheckCircle, CarFront } from 'lucide-react';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";

import { apiFetch } from '@/lib/api';

interface ExitAlert {
  id: number;
  alert_type: string;
  license_plate: string;
  detected_color: string | null;
  detected_model: string | null;
  expected_color: string | null;
  expected_model: string | null;
  image_url: string | null;
  created_at: string;
}

interface ParkingSession {
  id: number;
  license_plate: string;
  color: string;
  model: string;
  status: string;
  entry_time: string;
  car_image_url: string | null;
}

export default function ExitAlerts() {
  const [alerts, setAlerts] = useState<ExitAlert[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Drawer state
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState<ExitAlert | null>(null);
  const [paidSessions, setPaidSessions] = useState<ParkingSession[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<string>('');

  const fetchAlerts = async () => {
    try {
      const response = await apiFetch('/exit-alerts');
      if (response.ok) {
        const data = await response.json();
        setAlerts(data);
      }
    } catch (error) {
      console.error('Failed to fetch exit alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const handleDismiss = async (id: number) => {
    try {
      const response = await apiFetch(`/exit-alerts/${id}/dismiss`, {
        method: 'PUT'
      });
      if (response.ok) {
        setAlerts(alerts.filter(alert => alert.id !== id));
      }
    } catch (error) {
      console.error('Failed to dismiss alert:', error);
    }
  };

  const openMatchDrawer = async (alert: ExitAlert) => {
    setSelectedAlert(alert);
    setSelectedSessionId(''); // Reset selection
    setIsDrawerOpen(true);
    setLoadingSessions(true);

    try {
      // Fetch all PAID sessions (which means they have paid but haven't physically exited)
      const response = await apiFetch('/parking-sessions?status=paid&per_page=100');
      if (response.ok) {
        const data = await response.json();
        setPaidSessions(data.data || []);
      }
    } catch (error) {
      console.error('Failed to fetch paid sessions:', error);
    } finally {
      setLoadingSessions(false);
    }
  };

  const handleMatchAllowPass = async () => {
    if (!selectedAlert || !selectedSessionId) return;

    try {
      const response = await apiFetch(`/exit-alerts/${selectedAlert.id}/override`, {
        method: 'PUT',
        body: JSON.stringify({ session_id: parseInt(selectedSessionId) })
      });
      if (response.ok) {
        setAlerts(alerts.filter(alert => alert.id !== selectedAlert.id));
        setIsDrawerOpen(false);
        setSelectedAlert(null);
      }
    } catch (error) {
      console.error('Failed to match and override alert:', error);
    }
  };

  if (loading && alerts.length === 0) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        Loading exit gate alerts...
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <Card className="border-green-200 bg-green-50/50 shadow-sm">
        <CardContent className="p-8 text-center flex flex-col items-center justify-center">
          <CheckCircle className="h-12 w-12 text-green-600 mb-3" />
          <CardTitle className="text-xl font-bold text-green-800">No Pending Exit Alerts</CardTitle>
          <CardDescription className="text-green-700 mt-1 max-w-md">
            All exit gate operations are running normally. No vehicle attribute mismatches or missing plate issues detected.
          </CardDescription>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold tracking-tight text-gray-900 flex items-center">
        <AlertCircle className="mr-2 text-red-500" /> Action Required: Exit Gate Alerts
      </h2>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {alerts.map((alert) => (
          <Card key={alert.id} className="border-red-200 shadow-sm overflow-hidden flex flex-col">
            {alert.image_url && (
              <div className="relative h-48 w-full bg-black">
                <img
                  src={alert.image_url}
                  alt={`Car ${alert.license_plate}`}
                  className="object-contain w-full h-full"
                />
              </div>
            )}
            <CardHeader className="pb-3 bg-red-50">
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle className="text-lg font-bold text-red-700">
                    {alert.license_plate}
                  </CardTitle>
                  <CardDescription className="text-red-600 font-medium mt-1">
                    {alert.alert_type === 'plate_not_found' && 'Plate Not Found in Database'}
                    {alert.alert_type === 'color_mismatch' && 'Vehicle Color Mismatch'}
                    {alert.alert_type === 'model_mismatch' && 'Vehicle Model Mismatch'}
                  </CardDescription>
                </div>
                <Badge variant="destructive" className="uppercase text-[10px]">Pending</Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-4 flex-1 flex flex-col justify-between">
              <div className="space-y-3 mb-6">
                {alert.alert_type !== 'plate_not_found' && (
                  <>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div className="font-semibold text-gray-500">Detected:</div>
                      <div>{alert.detected_color} {alert.detected_model}</div>

                      <div className="font-semibold text-gray-500">Expected:</div>
                      <div>{alert.expected_color} {alert.expected_model}</div>
                    </div>
                  </>
                )}
                <div className="text-xs text-gray-400">
                  Time: {new Date(alert.created_at).toLocaleString()}
                </div>
              </div>

              <div className="flex gap-3 mt-auto">
                <Button
                  variant="outline"
                  className="flex-1 border-gray-300"
                  onClick={() => handleDismiss(alert.id)}
                >
                  Dismiss
                </Button>
                <Button
                  variant="default"
                  className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white"
                  onClick={() => openMatchDrawer(alert)}
                >
                  Match Session
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Sheet open={isDrawerOpen} onOpenChange={setIsDrawerOpen}>
        <SheetContent side="right" className="w-[500px] sm:max-w-[600px] flex flex-col p-0 border-l">
          <SheetHeader className="p-6 pb-4 border-b bg-gray-50/50">
            <SheetTitle className="text-xl">Match Exit Alert</SheetTitle>
            <SheetDescription>
              Select the correct PAID parking session for the vehicle waiting at the exit.
              If no match is found, close this drawer and click Dismiss.
            </SheetDescription>
            {selectedAlert && (
              <div className="mt-4 p-4 bg-red-50 border border-red-100 rounded-lg flex gap-4">
                {selectedAlert.image_url && (
                  <img src={selectedAlert.image_url} alt="Exit Camera" className="w-24 h-24 object-cover rounded-md bg-black" />
                )}
                <div>
                  <h4 className="font-semibold text-red-900 mb-1">Exit Camera Capture</h4>
                  <p className="text-sm text-red-700 font-medium">Plate: {selectedAlert.license_plate}</p>
                  <p className="text-sm text-red-700">Detected: {selectedAlert.detected_color} {selectedAlert.detected_model}</p>
                </div>
              </div>
            )}
          </SheetHeader>
          
          <div className="flex-1 overflow-y-auto min-h-0 p-6 space-y-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <CarFront className="w-5 h-5 text-gray-500" />
              Available PAID Sessions
            </h3>
            
            {loadingSessions ? (
              <div className="py-8 text-center text-sm text-gray-500">Loading active sessions...</div>
            ) : paidSessions.length === 0 ? (
              <div className="py-8 text-center p-4 border border-dashed rounded-lg bg-gray-50 text-gray-500">
                No PAID parking sessions found.
              </div>
            ) : (
              <RadioGroup value={selectedSessionId} onValueChange={setSelectedSessionId} className="space-y-3">
                {paidSessions.map((session) => (
                  <div key={session.id} className="flex items-start space-x-3">
                    <RadioGroupItem value={session.id.toString()} id={`session-${session.id}`} className="mt-4" />
                    <Label
                      htmlFor={`session-${session.id}`}
                      className={`flex-1 flex gap-4 p-3 rounded-lg border cursor-pointer hover:bg-gray-50 transition-colors ${selectedSessionId === session.id.toString() ? 'border-indigo-500 bg-indigo-50/50' : 'border-gray-200'}`}
                    >
                      {session.car_image_url ? (
                        <img src={session.car_image_url} alt="Car at Entry" className="w-24 h-24 object-cover rounded bg-black" />
                      ) : (
                        <div className="w-24 h-24 bg-gray-100 rounded flex items-center justify-center text-xs text-gray-400">
                          No Image
                        </div>
                      )}
                      <div className="flex-1 py-1">
                        <div className="font-bold text-lg text-gray-900 mb-1">{session.license_plate}</div>
                        <div className="text-sm text-gray-600">{session.color} {session.model}</div>
                        <div className="text-xs text-gray-400 mt-2">
                          Entry: {new Date(session.entry_time).toLocaleString()}
                        </div>
                      </div>
                    </Label>
                  </div>
                ))}
              </RadioGroup>
            )}
          </div>

          <div className="p-6 border-t bg-white">
            <Button 
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white"
              size="lg"
              disabled={!selectedSessionId}
              onClick={handleMatchAllowPass}
            >
              Allow Pass (Match Selected Session)
            </Button>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
