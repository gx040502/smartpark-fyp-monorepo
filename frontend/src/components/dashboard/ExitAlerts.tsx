'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react-native'; // Assuming lucide is used, we'll use lucide-react
import { AlertCircle } from 'lucide-react';
import Image from 'next/image';

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

export default function ExitAlerts() {
  const [alerts, setAlerts] = useState<ExitAlert[]>([]);
  const [loading, setLoading] = useState(true);

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

  const handleAction = async (id: number, action: 'dismiss' | 'override') => {
    try {
      const response = await apiFetch(`/exit-alerts/${id}/${action}`, {
        method: 'PUT'
      });
      if (response.ok) {
        // Remove the alert from the UI immediately
        setAlerts(alerts.filter(alert => alert.id !== id));
      }
    } catch (error) {
      console.error(`Failed to ${action} alert:`, error);
    }
  };

  if (loading && alerts.length === 0) {
    return null; // Or a loading skeleton
  }

  if (alerts.length === 0) {
    return null; // Don't show the section if there are no active alerts
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
                  onClick={() => handleAction(alert.id, 'dismiss')}
                >
                  Dismiss
                </Button>
                <Button 
                  variant="default" 
                  className="flex-1 bg-red-600 hover:bg-red-700 text-white"
                  onClick={() => handleAction(alert.id, 'override')}
                >
                  Allow Pass
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
