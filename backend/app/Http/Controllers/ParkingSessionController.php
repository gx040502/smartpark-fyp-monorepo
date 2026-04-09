<?php

namespace App\Http\Controllers;

use App\Models\ParkingSession;
use Illuminate\Http\Request;

class ParkingSessionController extends Controller
{
    /**
     * Display a paginated list of parking sessions with optional filters.
     */
    public function index(Request $request)
    {
        $query = ParkingSession::with('paymentReceipt');

        if ($request->filled('search')) {
            $search = $request->query('search');
            $query->where('license_plate', 'like', "%{$search}%");
        }

        if ($request->filled('status')) {
            $query->where('status', $request->query('status'));
        }

        if ($request->filled('color')) {
            $query->where('color', $request->query('color'));
        }

        if ($request->filled('model')) {
            $query->where('model', $request->query('model'));
        }
        
        // Default sorting
        $sortField = $request->query('sort_by', 'entry_time');
        $sortOrder = $request->query('sort_order', 'desc');
        
        $query->orderBy($sortField, $sortOrder);

        $sessions = $query->paginate($request->query('per_page', 15));

        return response()->json($sessions);
    }

    /**
     * Display the specified parking session with its receipt.
     */
    public function show(string $id)
    {
        $session = ParkingSession::with('paymentReceipt')->findOrFail($id);
        
        return response()->json($session);
    }
}
