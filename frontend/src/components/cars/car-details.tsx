'use client';

import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Car, FileText, Clock, Calendar, Receipt, DollarSign } from 'lucide-react';
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

  const getPaymentTypeBadge = (type: string) => {
    switch (type) {
      case 'initial': return <Badge variant="secondary" className="bg-indigo-100 text-indigo-700 text-xs">Initial</Badge>;
      case 'additional': return <Badge variant="secondary" className="bg-orange-100 text-orange-700 text-xs">Additional</Badge>;
      default: return <Badge variant="secondary" className="text-xs">{type}</Badge>;
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

  // Use payment_receipts (plural array) from the API
  const receipts = session.payment_receipts || [];
  const totalPaid = receipts.reduce((sum: number, r: any) => sum + parseFloat(r.total_amount || 0), 0);

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

            <div className="space-y-1 mt-4">
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
            {receipts.length > 0 ? (
              <div className="space-y-5">
                {/* Individual Receipts */}
                {receipts.map((receipt: any, index: number) => (
                  <div key={receipt.id} className={`space-y-3 ${index > 0 ? 'pt-4 border-t border-dashed border-gray-200' : ''}`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Receipt className="h-4 w-4 text-gray-400" />
                        <span className="font-semibold text-sm text-gray-700">
                          {receipt.receipt_number || `#RCT-${receipt.id.toString().padStart(6, '0')}`}
                        </span>
                      </div>
                      {getPaymentTypeBadge(receipt.payment_type)}
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div className="space-y-0.5">
                        <p className="text-xs text-muted-foreground">Payment Method</p>
                        <p className="font-medium flex items-center gap-1.5">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 inline-block"></span>
                          {receipt.payment_method}
                        </p>
                      </div>
                      <div className="space-y-0.5">
                        <p className="text-xs text-muted-foreground">Date</p>
                        <p className="font-medium">{new Date(receipt.payment_date).toLocaleString()}</p>
                      </div>
                    </div>

                    <div className="flex justify-end">
                      <span className="font-bold text-emerald-600">
                        RM {parseFloat(receipt.total_amount).toFixed(2)}
                      </span>
                    </div>
                  </div>
                ))}

                {/* Total Paid Summary */}
                <div className="pt-4 border-t-2 border-gray-200 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <DollarSign className="h-5 w-5 text-emerald-600" />
                    <CardTitle>Total Paid</CardTitle>
                  </div>
                  <span className="font-bold text-2xl text-emerald-600">
                    RM {totalPaid.toFixed(2)}
                  </span>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center space-y-3 py-6">
                <div className="h-12 w-12 rounded-full bg-amber-50 flex items-center justify-center">
                  <FileText className="h-6 w-6 text-amber-500" />
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">
                    {session.status === 'ENTER' ? 'Payment Pending' : 'No Receipt Linked'}
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1 max-w-[250px]">
                    {session.status === 'ENTER'
                      ? `Current running fee: RM ${parseFloat(session.amount_due || 0).toFixed(2)}`
                      : 'This session has not processed a payment receipt yet.'}
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
