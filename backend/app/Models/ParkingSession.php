<?php

namespace App\Models;

use App\Enums\ParkingStatus;
use Database\Factories\ParkingSessionFactory;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasOne;

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
            'entry_time'  => 'datetime',
            'exit_time'   => 'datetime',
            'amount_due'  => 'decimal:2',
            'status'      => ParkingStatus::class,
        ];
    }

    /**
     * Get the payment receipt associated with this parking session.
     */
    public function paymentReceipt(): HasOne
    {
        return $this->hasOne(PaymentReceipt::class);
    }
}
