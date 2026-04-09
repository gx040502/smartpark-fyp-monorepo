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
        $currentlyParked = ParkingSession::where('status', 'ENTER')->count();
        $totalCompleted = ParkingSession::where('status', 'COMPLETED')->count();

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
                'total_completed' => $totalCompleted
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
        $filter = $request->query('filter', 'today'); // 'today', 'week', default custom range
        $startDate = $request->query('start_date');
        $endDate = $request->query('end_date');

        $query = ParkingSession::query();

        if ($filter === 'today') {
            $query->whereDate('entry_time', Carbon::today());
        } elseif ($filter === 'week') {
            $query->whereBetween('entry_time', [Carbon::now()->startOfWeek(), Carbon::now()->endOfWeek()]);
        } elseif ($startDate && $endDate) {
            $query->whereBetween('entry_time', [Carbon::parse($startDate)->startOfDay(), Carbon::parse($endDate)->endOfDay()]);
        }

        // Group by hour
        $entries = $query->select(DB::raw('HOUR(entry_time) as hour'), DB::raw('count(*) as count'))
            ->groupBy('hour')
            ->orderBy('hour')
            ->pluck('count', 'hour')
            ->toArray();

        // Similarly for exits
        $exitQuery = ParkingSession::whereNotNull('exit_time');
        
        if ($filter === 'today') {
            $exitQuery->whereDate('exit_time', Carbon::today());
        } elseif ($filter === 'week') {
            $exitQuery->whereBetween('exit_time', [Carbon::now()->startOfWeek(), Carbon::now()->endOfWeek()]);
        } elseif ($startDate && $endDate) {
            $exitQuery->whereBetween('exit_time', [Carbon::parse($startDate)->startOfDay(), Carbon::parse($endDate)->endOfDay()]);
        }

        $exits = $exitQuery->select(DB::raw('HOUR(exit_time) as hour'), DB::raw('count(*) as count'))
            ->groupBy('hour')
            ->orderBy('hour')
            ->pluck('count', 'hour')
            ->toArray();

        $formattedData = [];
        for ($i = 0; $i < 24; $i++) {
            $formattedData[] = [
                'hour' => sprintf('%02d:00', $i),
                'entries' => $entries[$i] ?? 0,
                'exits' => $exits[$i] ?? 0,
            ];
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
}
