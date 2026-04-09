'use client';

import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Car, FileText, Clock, Calendar } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

export default function CarDetails({ initialSession, id }: { initialSession: any, id: string }) {
  const router = useRouter();
  
  // Directly attach the pre-fetched server state!
  const session = initialSession;

  const getStatusBadge = (s: string) => {
    switch (s) {
      case 'ENTER': return <Badge variant="secondary" className="bg-blue-100 text-blue-800 hover:bg-blue-200 text-sm py-1">ENTER</Badge>;
      case 'PAID': return <Badge variant="secondary" className="bg-amber-100 text-amber-800 hover:bg-amber-200 text-sm py-1">PAID</Badge>;
      case 'COMPLETED': return <Badge variant="secondary" className="bg-green-100 text-green-800 hover:bg-green-200 text-sm py-1">COMPLETED</Badge>;
      default: return <Badge>{s}</Badge>;
    }
  };

  if (!session) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[50vh]">
        <h2 className="text-xl font-bold bg-red-50 text-red-700 px-4 py-2 rounded-lg mb-4">Error 404: Session Not Found</h2>
        <Button variant="outline" onClick={() => router.push('/cars')}>Return to Directory</Button>
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8 flex-1 space-y-6 bg-slate-50 min-h-[calc(100vh-64px)] animate-in fade-in slide-in-from-bottom-4 duration-500">

      <div className="flex items-center gap-4">
        <Button variant="outline" size="icon" onClick={() => router.back()} className="h-10 w-10 shrink-0 shadow-sm border-gray-200">
          <ArrowLeft className="h-5 w-5 text-gray-600" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 flex items-center gap-3">
            {session.license_plate}
            {getStatusBadge(session.status)}
          </h1>
          <p className="text-muted-foreground mt-1">
            Complete trace of parking session #{session.id.toString().padStart(5, '0')}.
          </p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Vehicle Info */}
        <Card>
          <CardHeader className="bg-slate-50/50 border-b pb-4">
            <CardTitle className="text-lg flex items-center gap-2">
              <Car className="h-5 w-5 text-indigo-500" /> Vehicle Information
            </CardTitle>
          </CardHeader>

          <CardContent className="grid grid-cols-2 gap-4 pt-6">
            <div className="space-y-1">
              <CardTitle> Model</CardTitle>
              <CardDescription>{session.model}</CardDescription>
            </div>

            <div className="space-y-1">
              <CardTitle>Color Variant</CardTitle>
              <CardDescription>{session.color}</CardDescription>
            </div>

            <div className="space-y-1 mt-4">
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-3.5 w-3.5" />
                Entry Time
              </CardTitle>
              <CardDescription>{new Date(session.entry_time).toLocaleString()}</CardDescription>
            </div>

            <div className=" flexspace-y-1 mt-4">
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-3.5 w-3.5" />
                Exit Time
              </CardTitle>
              <CardDescription>
                {session.exit_time ? new Date(session.exit_time).toLocaleString() : <span className="text-blue-600">Still inside facility</span>}
              </CardDescription>
            </div>
          </CardContent>
        </Card>

        {/* Financial Info */}
        <Card className="shadow-sm border-gray-200">
          <CardHeader className="bg-slate-50/50 border-b pb-4">
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="h-5 w-5 text-emerald-500" /> Financial Audit
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            {session.payment_receipt ? (
              <div className="space-y-6">
                <div className="space-y-1">
                  <CardTitle>Receipt ID</CardTitle>
                  <CardDescription className="font-bold">#RCT-{session.payment_receipt.id.toString().padStart(6, '0')}</CardDescription>
                </div>

                <div className="space-y-1">
                  <CardTitle>Payment Method</CardTitle>
                  <CardDescription className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-emerald-500"></div>
                    {session.payment_receipt.payment_method}
                  </CardDescription>
                </div>

                <div className="space-y-1">
                  <CardTitle>Payment Date</CardTitle>
                  <CardDescription>{new Date(session.payment_receipt.payment_date).toLocaleString()}</CardDescription>
                </div>

                <div className="space-y-1 pt-2 border-t">
                  <CardTitle>Total Amount</CardTitle>
                  <CardDescription className="font-bold text-2xl text-emerald-600">
                    RM {parseFloat(session.payment_receipt.total_amount).toFixed(2)}
                  </CardDescription>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center space-y-3 py-6">
                <div className="h-12 w-12 rounded-full bg-amber-50 flex items-center justify-center">
                  <FileText className="h-6 w-6 text-amber-500" />
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">No Receipt Linked</h3>
                  <p className="text-sm text-muted-foreground mt-1 max-w-[250px]">
                    This session has not processed a payment receipt yet or it is still active inside the facility.
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div >
  );
}
