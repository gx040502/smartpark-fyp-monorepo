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
import { Search, ChevronLeft, ChevronRight, X } from 'lucide-react';

export default function CarList({ initialData, searchParams, filterOptions }: {
  initialData: CarListPaginationParams,
  searchParams: { [key: string]: string | undefined },
  filterOptions: { colors: string[], models: string[] } | null,
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
  const [model, setModel] = useState(searchParams?.model || 'all');
  const [dateField, setDateField] = useState(searchParams?.date_field || 'entry_time');
  const [dateFrom, setDateFrom] = useState(searchParams?.date_from || '');
  const [dateTo, setDateTo] = useState(searchParams?.date_to || '');

  const colors = filterOptions?.colors || [];
  const models = filterOptions?.models || [];

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

  const updateMultipleQuery = (updates: Record<string, string>) => {
    const params = new URLSearchParams(window.location.search);
    for (const [key, value] of Object.entries(updates)) {
      if (value && value !== 'all') {
        params.set(key, value);
      } else {
        params.delete(key);
      }
    }
    params.delete('page');
    router.push(`${pathname}?${params.toString()}`);
  };

  const clearDateRange = () => {
    setDateFrom('');
    setDateTo('');
    setDateField('entry_time');
    updateMultipleQuery({ date_from: '', date_to: '', date_field: '' });
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

  const hasActiveDateFilter = dateFrom || dateTo;

  return (
    <div className="flex flex-1 flex-col gap-4 p-4 pt-0 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <Card>
        <CardHeader className="flex flex-col gap-4 space-y-0">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <CardTitle>Cars Directory</CardTitle>
            <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
              {/* Search */}
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

              {/* Status Filter */}
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

              {/* Color Filter — dynamic from DB */}
              <Select value={color} onValueChange={(val) => { setColor(val || 'all'); updateQuery('color', val || 'all'); }}>
                <SelectTrigger className="w-full sm:w-[130px] hidden md:flex">
                  <SelectValue placeholder="Colour" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Colours</SelectItem>
                  {colors.map((c) => (
                    <SelectItem key={c} value={c}>{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Model Filter — dynamic from DB */}
              <Select value={model} onValueChange={(val) => { setModel(val || 'all'); updateQuery('model', val || 'all'); }}>
                <SelectTrigger className="w-full sm:w-[160px] hidden md:flex">
                  <SelectValue placeholder="Model" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Models</SelectItem>
                  {models.map((m) => (
                    <SelectItem key={m} value={m}>{m}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Date Range Filter Row */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
            <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">Date Range:</span>
            <Select value={dateField} onValueChange={(val) => { setDateField(val); if (dateFrom || dateTo) updateQuery('date_field', val); }}>
              <SelectTrigger className="w-full sm:w-[140px]">
                <SelectValue placeholder="Field" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="entry_time">Entry Time</SelectItem>
                <SelectItem value="exit_time">Exit Time</SelectItem>
              </SelectContent>
            </Select>
            <Input
              type="date"
              className="w-full sm:w-[160px]"
              value={dateFrom}
              onChange={(e) => { setDateFrom(e.target.value); updateMultipleQuery({ date_from: e.target.value, date_to: dateTo, date_field: dateField }); }}
              placeholder="From"
            />
            <span className="text-sm text-muted-foreground hidden sm:inline">to</span>
            <Input
              type="date"
              className="w-full sm:w-[160px]"
              value={dateTo}
              onChange={(e) => { setDateTo(e.target.value); updateMultipleQuery({ date_from: dateFrom, date_to: e.target.value, date_field: dateField }); }}
              placeholder="To"
            />
            {hasActiveDateFilter && (
              <Button variant="ghost" size="sm" onClick={clearDateRange} className="text-muted-foreground hover:text-foreground">
                <X className="h-4 w-4 mr-1" /> Clear
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>License Plate</TableHead>
                <TableHead>Image</TableHead>
                <TableHead>Colour</TableHead>
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

                  return (
                    <TableRow
                      key={row.id}
                      className="hover:bg-accent cursor-pointer transition-colors"
                      onClick={() => openDetails(row)}
                    >
                      <TableCell className="font-medium tracking-wider">{row.license_plate}</TableCell>
                      <TableCell>
                        {row.car_image_url ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={row.car_image_url} alt="Car" className="h-10 w-16 object-cover rounded shadow-sm border border-gray-200" />
                        ) : (
                          <div className="h-10 w-16 bg-gray-100 rounded flex items-center justify-center text-[10px] text-gray-400 border border-gray-200 shadow-sm">No Image</div>
                        )}
                      </TableCell>
                      <TableCell className="text-sm">{row.color}</TableCell>
                      <TableCell>
                        <div className="font-medium text-sm text-gray-900">{row.model}</div>
                      </TableCell>
                      <TableCell className="text-sm">
                        {entryTime.toLocaleDateString()} <br />
                        <span className="text-muted-foreground">{entryTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </TableCell>
                      <TableCell className="text-sm">{row.duration || '--'}</TableCell>
                      <TableCell>
                        {parseFloat(row.amount_due) > 0
                          ? parseFloat(row.amount_due).toFixed(2)
                          : parseFloat(row.amount_due) === 0
                            ? <Badge variant="secondary" className="bg-emerald-100 text-emerald-800 hover:bg-emerald-200">FREE</Badge>
                            : '-'}
                      </TableCell>
                      <TableCell>{getStatusBadge(row.status)}</TableCell>
                    </TableRow>
                  );
                })
              ) : (
                <TableRow>
                  <TableCell colSpan={7} className="text-center">
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
