'use client';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export default function PaymentInsightsChart({ initialData }: { initialData: any }) {
  if (!initialData || !initialData.methods) {
    return (
      <Card className="shadow-sm animate-pulse">
        <CardHeader className="h-14"></CardHeader>
        <CardContent className="h-64"></CardContent>
      </Card>
    );
  }

  const { methods } = initialData;

  // Custom colors for payment methods
  const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6'];

  return (
    <Card className="shadow-sm flex flex-col h-full border-gray-200">
      <CardHeader>
        <CardTitle>Payment Methods</CardTitle>
        <CardDescription>Breakdown of how users prefer to pay</CardDescription>
      </CardHeader>
      <CardContent className="flex-1 pb-4">
        <div className="flex flex-col h-64">
          {methods.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">No data available</div>
          ) : (
            <div className="flex-1 w-full h-full relative">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={methods}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="count"
                    nameKey="payment_method"
                  >
                    {methods.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    formatter={(value: number, name: string, props: any) => [
                      `${value} txns (RM ${parseFloat(props.payload.revenue).toFixed(2)})`, 
                      name
                    ]}
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
