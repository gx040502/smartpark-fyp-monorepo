<?php

namespace Database\Factories;

use App\Models\ParkingSession;
use App\Models\PaymentReceipt;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<PaymentReceipt>
 */
class PaymentReceiptFactory extends Factory
{
    protected $model = PaymentReceipt::class;

    /**
     * Available payment methods.
     */
    private const PAYMENT_METHODS = [
        'Credit Card',
        'Debit Card',
        'Touch n Go',
    ];

    /**
     * Define the model's default state.
     *
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            'parking_session_id' => ParkingSession::factory(),
            'total_amount'       => 0, // Will be set by seeder to match session amount
            'payment_date'       => now(),
            'payment_method'     => $this->faker->randomElement(self::PAYMENT_METHODS),
        ];
    }

    /**
     * Create a receipt linked to a specific parking session.
     * Automatically mirrors the session's amount_due and sets a realistic payment_date.
     */
    public function forSession(ParkingSession $session): static
    {
        // Payment happens between entry_time and exit_time (or at exit_time)
        $paymentDate = $session->exit_time
            ? $this->faker->dateTimeBetween($session->entry_time, $session->exit_time)
            : $session->entry_time;

        return $this->state(fn (array $attributes) => [
            'parking_session_id' => $session->id,
            'total_amount'       => $session->amount_due,
            'payment_date'       => $paymentDate,
        ]);
    }
}
