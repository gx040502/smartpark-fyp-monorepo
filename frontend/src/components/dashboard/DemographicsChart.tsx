'use client';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';

export default function DemographicsChart({ initialData }: { initialData: any }) {
  if (!initialData || (!initialData.colors && !initialData.models)) {
    return (
      <Card className="col-span-2 shadow-sm animate-pulse">
        <CardHeader className="h-14"></CardHeader>
        <CardContent className="h-64"></CardContent>
      </Card>
    );
  }

  const { colors, models } = initialData;

  // Custom colors for the pie chart
  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#64748b'];

  return (
    <Card className="col-span-1 md:col-span-2 shadow-sm flex flex-col h-full border-gray-200">
      <CardHeader>
        <CardTitle>Vehicle Demographics</CardTitle>
        <CardDescription>Top colors and models of parked vehicles</CardDescription>
      </CardHeader>
      <CardContent className="flex-1 pb-4">
        <div className="grid md:grid-cols-2 h-full gap-8">
          
          {/* Colors Donut Chart */}
          <div className="flex flex-col h-64">
            <h4 className="text-sm font-semibold text-center text-gray-500 mb-2">Color Distribution</h4>
            {colors.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">No data available</div>
            ) : (
              <div className="flex-1 w-full h-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={colors}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="count"
                      nameKey="color"
                    >
                      {colors.map((entry: any, index: number) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      formatter={(value: number, name: string) => [`${value} cars`, name]}
                      contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
            <div className="flex justify-center flex-wrap gap-3 mt-2">
              {colors.slice(0, 5).map((entry: any, index: number) => (
                <div key={index} className="flex items-center text-xs text-gray-600">
                  <div className="w-2 h-2 rounded-full mr-1.5" style={{ backgroundColor: COLORS[index % COLORS.length] }}></div>
                  {entry.color} ({entry.count})
                </div>
              ))}
            </div>
          </div>

          {/* Models Bar Chart */}
          <div className="flex flex-col h-64">
            <h4 className="text-sm font-semibold text-center text-gray-500 mb-2">Top Car Models</h4>
            {models.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">No data available</div>
            ) : (
              <div className="flex-1 w-full h-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={models} layout="vertical" margin={{ top: 0, right: 0, left: 10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} opacity={0.5} />
                    <XAxis type="number" hide />
                    <YAxis 
                      type="category" 
                      dataKey="model" 
                      width={80} 
                      axisLine={false} 
                      tickLine={false}
                      tick={{ fontSize: 12, fill: '#64748b' }}
                    />
                    <Tooltip 
                      cursor={{fill: '#f8fafc'}}
                      formatter={(value: number) => [`${value} cars`, 'Count']}
                      contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    />
                    <Bar dataKey="count" fill="#8b5cf6" radius={[0, 4, 4, 0]} barSize={20} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
          
        </div>
      </CardContent>
    </Card>
  );
}
