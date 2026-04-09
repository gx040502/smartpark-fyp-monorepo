'use client';

import { useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { CarListPaginationParams } from '@/app/actions/cars';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Search, ChevronLeft, ChevronRight } from 'lucide-react';

export default function CarList({ 
  initialData, 
  searchParams 
}: { 
  initialData: CarListPaginationParams, 
  searchParams: { [key: string]: string | undefined } 
}) {
  const router = useRouter();
  const pathname = usePathname();
  
  // No more apiFetch! The server passes the exact rendered view.
  const data = initialData?.data || [];
  const pagination = initialData ? {
    current_page: initialData.current_page,
    last_page: initialData.last_page,
    total: initialData.total
  } : { current_page: 1, last_page: 1, total: 0 };
  
  // Filters mirror the URL accurately instead of empty local state
  const [search, setSearch] = useState(searchParams?.search || '');
  const [status, setStatus] = useState(searchParams?.status || 'all');
  const [color, setColor] = useState(searchParams?.color || 'all');
  
  // Push query dynamically through URL to invoke NextJS SSR rerender
  const updateQuery = (key: string, value: string) => {
    const params = new URLSearchParams(window.location.search);
    if (value && value !== 'all') {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    // Reset page to 1 on any filter change
    if (key !== 'page') params.delete('page');
    
    router.push(`${pathname}?${params.toString()}`);
  };

  const handleSearchSubmit = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      updateQuery('search', search);
    }
  };

  const openDetails = (session: any) => {
    router.push(`/cars/${session.id}`);
  };

  const getStatusBadge = (s: string) => {
    switch (s) {
      case 'ENTER': return <Badge variant="secondary" className="bg-blue-100 text-blue-800 hover:bg-blue-200">ENTER</Badge>;
      case 'PAID': return <Badge variant="secondary" className="bg-amber-100 text-amber-800 hover:bg-amber-200">PAID</Badge>;
      case 'COMPLETED': return <Badge variant="secondary" className="bg-green-100 text-green-800 hover:bg-green-200">COMPLETED</Badge>;
      default: return <Badge>{s}</Badge>;
    }
  };

  return (
    <div className="flex flex-1 flex-col gap-4 p-4 pt-0 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <Card>
        <CardHeader className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 space-y-0">
          <CardTitle>Cars Directory</CardTitle>
          <div className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search License Plate (Press Enter)..."
                className="pl-9"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={handleSearchSubmit}
              />
            </div>
            
            <Select value={status} onValueChange={(val) => { setStatus(val || 'all'); updateQuery('status', val || 'all'); }}>
              <SelectTrigger className="w-full sm:w-[140px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="ENTER">Enter</SelectItem>
                <SelectItem value="PAID">Paid</SelectItem>
                <SelectItem value="COMPLETED">Completed</SelectItem>
              </SelectContent>
            </Select>

            <Select value={color} onValueChange={(val) => { setColor(val || 'all'); updateQuery('color', val || 'all'); }}>
              <SelectTrigger className="w-full sm:w-[130px] hidden md:flex">
                <SelectValue placeholder="Color" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Colors</SelectItem>
                <SelectItem value="White">White</SelectItem>
                <SelectItem value="Black">Black</SelectItem>
                <SelectItem value="Silver">Silver</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>License Plate</TableHead>
                <TableHead>Vehicle</TableHead>
                <TableHead>Entry Time</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Amount (RM)</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.length > 0 ? (
                data.map((row: any) => {
                  const entryTime = new Date(row.entry_time);
                  const exitTime = row.exit_time ? new Date(row.exit_time) : null;
                  const durationStr = exitTime 
                    ? (() => {
                        const diffMs = exitTime.getTime() - entryTime.getTime();
                        const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
                        const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
                        return `${diffHrs}h ${diffMins}m`;
                      })()
                    : '--';

                  return (
                    <TableRow 
                      key={row.id} 
                      className="hover:bg-accent cursor-pointer transition-colors" 
                      onClick={() => openDetails(row)}
                    >
                      <TableCell className="font-medium tracking-wider">{row.license_plate}</TableCell>
                      <TableCell>
                        <div className="font-medium text-sm text-gray-900">{row.model}</div>
                        <div className="text-xs text-muted-foreground">{row.color}</div>
                      </TableCell>
                      <TableCell className="text-sm">
                        {entryTime.toLocaleDateString()} <br />
                        <span className="text-muted-foreground">{entryTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </TableCell>
                      <TableCell className="text-sm">{durationStr}</TableCell>
                      <TableCell>{row.amount_due > 0 ? parseFloat(row.amount_due).toFixed(2) : '-'}</TableCell>
                      <TableCell>{getStatusBadge(row.status)}</TableCell>
                    </TableRow>
                  );
                })
              ) : (
                <TableRow>
                  <TableCell colSpan={6} className="text-center">
                    <CardDescription>No parking sessions found matching your criteria.</CardDescription>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>

          {/* Pagination */}
          <div className="flex items-center justify-between pt-4">
            <CardDescription className="text-sm">
              Showing {pagination.total > 0 ? (pagination.current_page - 1) * 15 + 1 : 0} to {Math.min(pagination.current_page * 15, pagination.total)} of {pagination.total} results
            </CardDescription>
            <div className="flex gap-2">
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => updateQuery('page', String(pagination.current_page - 1))}
                disabled={pagination.current_page <= 1}
              >
                <ChevronLeft className="h-4 w-4 mr-1" /> Prev
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => updateQuery('page', String(pagination.current_page + 1))}
                disabled={pagination.current_page >= pagination.last_page || pagination.last_page === 0}
              >
                Next <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
