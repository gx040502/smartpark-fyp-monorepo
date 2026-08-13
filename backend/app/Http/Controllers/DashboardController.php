<?php

namespace App\Http\Controllers;

use App\Models\ParkingSession;
use App\Models\PaymentReceipt;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;

class DashboardController extends Controller
{
    /**
     * Get high-level metrics: Occupancy, Daily Revenue, Avg Dwell Time
     */
    public function metrics()
    {
        $currentlyParked = ParkingSession::where('status', 'ENTER')
            ->whereDate('entry_time', Carbon::today())
            ->count();
            
        $paidAndWaiting = ParkingSession::where('status', 'PAID')
            ->whereDate('entry_time', Carbon::today())
            ->count();
        $completedToday = ParkingSession::where('status', 'COMPLETED')
            ->whereDate('exit_time', Carbon::today())
            ->count();

        $dailyRevenue = PaymentReceipt::whereDate('payment_date', Carbon::today())->sum('total_amount');

        // Calculate average dwell time (in minutes) for completed sessions
        $completedSessions = ParkingSession::where('status', 'COMPLETED')
            ->whereNotNull('exit_time')
            ->get();

        $totalMinutes = 0;
        foreach ($completedSessions as $session) {
            $totalMinutes += $session->entry_time->diffInMinutes($session->exit_time);
        }
        
        $avgDwellTime = $completedSessions->count() > 0 ? round($totalMinutes / $completedSessions->count()) : 0;
        
        // Format for display
        $avgDwellTimeFormatted = floor($avgDwellTime / 60) . 'h ' . ($avgDwellTime % 60) . 'm';

        return response()->json([
            'occupancy' => [
                'current' => $currentlyParked,
                'paid' => $paidAndWaiting,
                'total_completed' => $completedToday
            ],
            'daily_revenue' => $dailyRevenue,
            'avg_dwell_time' => $avgDwellTimeFormatted,
            'avg_dwell_time_minutes' => $avgDwellTime
        ]);
    }

    /**
     * Get aggregate entry/exit data for Peak Hours chart based on date range
     */
    public function peakHours(Request $request)
    {
        $filter = $request->query('filter', 'today'); // 'today', 'week', custom
        $startDateStr = $request->query('start_date');
        $endDateStr = $request->query('end_date');

        // Determine Start, End, and Grouping Logic
        if ($filter === 'today') {
            $start = Carbon::today();
            $end = Carbon::today()->endOfDay();
        } elseif ($filter === 'week') {
            $start = Carbon::now()->startOfWeek();
            $end = Carbon::now()->endOfWeek();
        } elseif ($startDateStr && $endDateStr) {
            $start = Carbon::parse($startDateStr)->startOfDay();
            $end = Carbon::parse($endDateStr)->endOfDay();
        } else {
            $start = Carbon::today();
            $end = Carbon::today()->endOfDay();
        }

        $daysDiff = $start->diffInDays($end);

        if ($daysDiff < 2) {
            $groupBy = 'hour'; // 00:00 to 23:00
            $selectFormat = "DATE_FORMAT(%s, '%%H:00')"; // For MySQL
            // SQLite compatibility (if using SQLite for local dev): $selectFormat = "strftime('%%H:00', %s)";
        } elseif ($daysDiff <= 31) {
            $groupBy = 'date';
            $selectFormat = "DATE_FORMAT(%s, '%%Y-%%m-%%d')";
        } else {
            $groupBy = 'month';
            $selectFormat = "DATE_FORMAT(%s, '%%Y-%%m')";
        }
        
        // Handle SQLite (since artisan serve on Windows might be using SQLite)
        $isSqlite = DB::connection()->getDriverName() === 'sqlite';
        if ($isSqlite) {
            if ($groupBy === 'hour') $selectFormat = "strftime('%%H:00', %s)";
            elseif ($groupBy === 'date') $selectFormat = "strftime('%%Y-%%m-%%d', %s)";
            else $selectFormat = "strftime('%%Y-%%m', %s)";
        }

        // Fetch Entries
        $entriesRaw = sprintf($selectFormat, 'entry_time');
        $entries = ParkingSession::whereBetween('entry_time', [$start, $end])
            ->select(DB::raw("$entriesRaw as label"), DB::raw('count(*) as count'))
            ->groupBy('label')
            ->pluck('count', 'label')
            ->toArray();

        // Fetch Exits
        $exitsRaw = sprintf($selectFormat, 'exit_time');
        $exits = ParkingSession::whereNotNull('exit_time')
            ->whereBetween('exit_time', [$start, $end])
            ->select(DB::raw("$exitsRaw as label"), DB::raw('count(*) as count'))
            ->groupBy('label')
            ->pluck('count', 'label')
            ->toArray();

        $formattedData = [];

        // Generate full date range so there are no gaps
        if ($groupBy === 'hour') {
            for ($i = 0; $i < 24; $i++) {
                $label = sprintf('%02d:00', $i);
                $formattedData[] = [
                    'label' => $label,
                    'entries' => $entries[$label] ?? 0,
                    'exits' => $exits[$label] ?? 0,
                ];
            }
        } elseif ($groupBy === 'date') {
            $current = $start->copy();
            while ($current <= $end) {
                $label = $current->format('Y-m-d');
                $formattedData[] = [
                    'label' => $current->format('d M'), // e.g. 05 Aug
                    'entries' => $entries[$label] ?? 0,
                    'exits' => $exits[$label] ?? 0,
                ];
                $current->addDay();
            }
        } elseif ($groupBy === 'month') {
            $current = $start->copy()->startOfMonth();
            while ($current <= $end) {
                $label = $current->format('Y-m');
                $formattedData[] = [
                    'label' => $current->format('M Y'), // e.g. Aug 2026
                    'entries' => $entries[$label] ?? 0,
                    'exits' => $exits[$label] ?? 0,
                ];
                $current->addMonth();
            }
        }

        return response()->json($formattedData);
    }

    /**
     * Get revenue trends for the past 7 days
     */
    public function revenueTrends()
    {
        $trends = [];
        
        for ($i = 6; $i >= 0; $i--) {
            $date = Carbon::today()->subDays($i);
            $revenue = PaymentReceipt::whereDate('payment_date', $date)
                ->sum('total_amount');
                
            $trends[] = [
                'date' => $date->format('Y-m-d'),
                'day' => $date->format('D'), // Mon, Tue, etc.
                'revenue' => (float) $revenue
            ];
        }

        return response()->json($trends);
    }

    /**
     * Get Vehicle Demographics (Colors and Models)
     */
    public function demographics()
    {
        $colors = ParkingSession::select('color', DB::raw('count(*) as count'))
            ->groupBy('color')
            ->orderBy('count', 'desc')
            ->get();

        $models = ParkingSession::select('model', DB::raw('count(*) as count'))
            ->groupBy('model')
            ->orderBy('count', 'desc')
            ->limit(5)
            ->get();

        return response()->json([
            'colors' => $colors,
            'models' => $models
        ]);
    }

    /**
     * Get Payment Insights
     */
    public function paymentInsights()
    {
        $paymentMethods = PaymentReceipt::select('payment_method', DB::raw('count(*) as count'), DB::raw('sum(total_amount) as revenue'))
            ->groupBy('payment_method')
            ->orderBy('count', 'desc')
            ->get();

        $overdueRevenue = PaymentReceipt::where('payment_type', 'additional')
            ->sum('total_amount');

        return response()->json([
            'methods' => $paymentMethods,
            'overdue_revenue' => (float) $overdueRevenue
        ]);
    }
}
