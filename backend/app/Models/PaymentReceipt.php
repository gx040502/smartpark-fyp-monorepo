<?php

namespace App\Models;

use Database\Factories\PaymentReceiptFactory;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class PaymentReceipt extends Model
{
    /** @use HasFactory<PaymentReceiptFactory> */
    use HasFactory;

    /**
     * The attributes that are mass assignable.
     *
     * @var list<string>
     */
    protected $fillable = [
        'parking_session_id',
        'total_amount',
        'payment_date',
        'payment_method',
    ];

    /**
     * Get the attributes that should be cast.
     *
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'total_amount'   => 'decimal:2',
            'payment_date'   => 'datetime',
        ];
    }

    /**
     * Get the parking session that this receipt belongs to.
     */
    public function parkingSession(): BelongsTo
    {
        return $this->belongsTo(ParkingSession::class);
    }
}
