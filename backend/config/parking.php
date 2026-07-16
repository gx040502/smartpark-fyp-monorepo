<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Parking Rate
    |--------------------------------------------------------------------------
    |
    | The hourly rate (in RM) charged for parking. Duration is rounded up
    | to the nearest hour. For example, 1h 10m is billed as 2 hours.
    |
    */
    'rate_per_hour' => 2.00,

    /*
    |--------------------------------------------------------------------------
    | Grace Period (Minutes)
    |--------------------------------------------------------------------------
    |
    | The number of minutes a driver is allowed to exit after making a payment
    | before additional charges are applied.
    |
    */
    'grace_period_minutes' => 15,

    /*
    |--------------------------------------------------------------------------
    | Free Exit Period (Minutes)
    |--------------------------------------------------------------------------
    |
    | The number of minutes a driver is allowed to exit for free after entry.
    |
    */
    'free_exit_minutes' => 15,

];
