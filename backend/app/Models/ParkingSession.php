<?php

namespace App\Models;

use App\Enums\ParkingStatus;
use Database\Factories\ParkingSessionFactory;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Carbon;

class ParkingSession extends Model
{
    /** @use HasFactory<ParkingSessionFactory> */
    use HasFactory;

    /**
     * The attributes that are mass assignable.
     *
     * @var list<string>
     */
    protected $fillable = [
        'license_plate',
        'color',
        'model',
        'entry_time',
        'exit_time',
        'grace_end_time',
        'amount_due',
        'status',
    ];

    /**
     * Get the attributes that should be cast.
     *
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'entry_time'     => 'datetime',
            'exit_time'      => 'datetime',
            'grace_end_time' => 'datetime',
            'amount_due'     => 'decimal:2',
            'status'         => ParkingStatus::class,
        ];
    }

    /**
     * Calculate parking fee from entry to a given end time.
     * Uses the configured rate: RM X per hour, rounded up to nearest hour.
     */
    public function calculateParkingFee(?Carbon $endTime = null): float
    {
        $endTime = $endTime ?? now();
        $minutes = $this->entry_time->diffInMinutes($endTime);
        $hours = max(1, ceil($minutes / 60));

        return $hours * config('parking.rate_per_hour');
    }

    /**
     * Get all payment receipts associated with this parking session.
     */
    public function paymentReceipts(): HasMany
    {
        return $this->hasMany(PaymentReceipt::class);
    }
}
