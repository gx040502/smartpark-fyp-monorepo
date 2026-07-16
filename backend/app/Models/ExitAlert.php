<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class ExitAlert extends Model
{
    protected $fillable = [
        'alert_type',
        'license_plate',
        'detected_color',
        'detected_model',
        'expected_color',
        'expected_model',
        'image_path',
        'session_id',
        'status',
    ];

    public function parkingSession()
    {
        return $this->belongsTo(ParkingSession::class, 'session_id');
    }
}
