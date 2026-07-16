import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import DriverLoginScreen from '../screens/DriverLoginScreen';
import PaymentDetailsScreen from '../screens/PaymentDetailsScreen';
import SelectMethodScreen from '../screens/SelectMethodScreen';
import ReceiptScreen from '../screens/ReceiptScreen';
import AdditionalPaymentScreen from '../screens/AdditionalPaymentScreen';

export type RootStackParamList = {
  DriverLogin: undefined;
  PaymentDetails: { licensePlate: string; sessionData: any };
  SelectMethod: { sessionData: any };
  Receipt: { receiptData: any; sessionData: any };
  AdditionalPayment: { sessionData: any };
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function AppNavigator() {
  return (
    <Stack.Navigator
      initialRouteName="DriverLogin"
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: '#ffffff' },
      }}
    >
      <Stack.Screen name="DriverLogin" component={DriverLoginScreen} />
      <Stack.Screen name="PaymentDetails" component={PaymentDetailsScreen} />
      <Stack.Screen name="SelectMethod" component={SelectMethodScreen} />
      <Stack.Screen name="Receipt" component={ReceiptScreen} />
      <Stack.Screen name="AdditionalPayment" component={AdditionalPaymentScreen} />
    </Stack.Navigator>
  );
}
