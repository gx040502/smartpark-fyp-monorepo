<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('payment_receipts', function (Blueprint $table) {
            $table->id();
            $table->foreignId('parking_session_id')
                  ->constrained('parking_sessions')
                  ->cascadeOnDelete();
            $table->decimal('total_amount', 8, 2);
            $table->timestamp('payment_date');
            $table->string('payment_method');
            $table->timestamps();

            // Index for revenue queries
            $table->index('payment_date');
            $table->index('payment_method');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('payment_receipts');
    }
};
