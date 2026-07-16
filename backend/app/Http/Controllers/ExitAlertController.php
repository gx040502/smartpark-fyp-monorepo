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
    
    public function override($id)
    {
        $alert = ExitAlert::findOrFail($id);
        
        // Complete the parking session if one exists
        if ($alert->session_id) {
            $alert->parkingSession()->update([
                'status'    => ParkingStatus::COMPLETED->value,
                'exit_time' => now(),
            ]);
        }
        
        $alert->update(['status' => 'OVERRIDDEN']);
        
        return response()->json(['message' => 'Alert overridden and car allowed to pass.']);
    }
}
