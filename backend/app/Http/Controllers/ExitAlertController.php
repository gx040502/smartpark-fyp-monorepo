<?php

namespace App\Http\Controllers;

use App\Models\ExitAlert;
use App\Enums\ParkingStatus;
use Illuminate\Http\Request;

class ExitAlertController extends Controller
{
    public function index()
    {
        $alerts = ExitAlert::with('parkingSession')
            ->where('status', 'PENDING')
            ->orderBy('created_at', 'desc')
            ->get();
            
        // Map the image URL for frontend
        $alerts->transform(function ($alert) {
            if ($alert->image_path) {
                $alert->image_url = asset('storage/' . $alert->image_path);
            }
            return $alert;
        });
            
        return response()->json($alerts);
    }
    
    public function dismiss($id)
    {
        $alert = ExitAlert::findOrFail($id);
        $alert->update(['status' => 'DISMISSED']);
        
        return response()->json(['message' => 'Alert dismissed successfully.']);
    }
    
    public function override(Request $request, $id)
    {
        $alert = ExitAlert::findOrFail($id);
        
        // If a specific session_id is provided, match the alert to it
        if ($request->has('session_id')) {
            $session = \App\Models\ParkingSession::findOrFail($request->session_id);
            $session->update([
                'status'    => ParkingStatus::COMPLETED->value,
                'exit_time' => now(),
            ]);
            // Link the alert to this session so we know how it was resolved
            $alert->session_id = $session->id;
        } 
        // Otherwise use the alert's existing session_id if present
        else if ($alert->session_id) {
            $alert->parkingSession()->update([
                'status'    => ParkingStatus::COMPLETED->value,
                'exit_time' => now(),
            ]);
        }
        
        $alert->update(['status' => 'OVERRIDDEN']);
        
        return response()->json(['message' => 'Alert overridden and car allowed to pass.']);
    }
}
