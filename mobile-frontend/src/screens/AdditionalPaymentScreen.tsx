import React, { useState } from 'react';
import { View, Text, TouchableOpacity, ScrollView, ActivityIndicator, Alert } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '../navigation/AppNavigator';
import { ArrowLeft, CreditCard, Wallet, Circle, CheckCircle2, AlertTriangle } from 'lucide-react-native';
import apiClient from '../api/client';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'AdditionalPayment'>;
  route: RouteProp<RootStackParamList, 'AdditionalPayment'>;
};

export default function AdditionalPaymentScreen({ navigation, route }: Props) {
  const insets = useSafeAreaInsets();
  const { sessionData } = route.params;
  const [selectedMethod, setSelectedMethod] = useState<string>('Credit Card');
  const [loading, setLoading] = useState(false);

  const paymentMethods = [
    { id: 'Credit Card', label: 'Credit Card', icon: CreditCard },
    { id: 'Touch n Go', label: "Touch 'n Go", icon: Wallet },
  ];

  const overdueMinutes = sessionData.overdue_minutes || 0;
  const extraCharge = parseFloat(sessionData.extra_charge || '0');
  const originalFee = parseFloat(sessionData.original_fee || sessionData.amount_due || '0');
  const totalPaid = parseFloat(sessionData.total_paid || '0');

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    let normalized = dateString;
    if (!normalized.includes('T')) normalized = normalized.replace(' ', 'T');
    if (!normalized.endsWith('Z') && !normalized.includes('+')) normalized += 'Z';
    
    const date = new Date(normalized);
    // Add 8 hours for Malaysia Time
    const myTime = new Date(date.getTime() + (8 * 60 * 60 * 1000));
    
    const day = myTime.getUTCDate();
    const month = myTime.getUTCMonth() + 1;
    const year = myTime.getUTCFullYear();
    
    let hours = myTime.getUTCHours();
    const minutes = myTime.getUTCMinutes();
    const seconds = myTime.getUTCSeconds();
    
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12;
    
    const minStr = minutes < 10 ? '0' + minutes : minutes;
    const secStr = seconds < 10 ? '0' + seconds : seconds;
    
    return `${month}/${day}/${year}, ${hours}:${minStr}:${secStr} ${ampm}`;
  };

  const handlePayAdditional = async () => {
    setLoading(true);
    try {
      const response = await apiClient.post(`/parking-sessions/${sessionData.id}/pay-additional`, {
        payment_method: selectedMethod,
      });

      const { receipt, session } = response.data;
      navigation.navigate('Receipt', {
        receiptData: receipt,
        sessionData: session,
      });
    } catch (error: any) {
      const message = error.response?.data?.message || 'An error occurred while processing your payment.';
      Alert.alert('Payment Failed', message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View className="flex-1 bg-white" style={{ paddingTop: insets.top, paddingBottom: insets.bottom }}>
      {/* Header */}
      <View className="flex-row items-center px-4 py-3 border-b border-gray-100">
        <TouchableOpacity className="p-2" onPress={() => navigation.goBack()}>
          <ArrowLeft size={24} color="#333" />
        </TouchableOpacity>
        <Text className="font-interBold text-lg ml-2 text-gray-800">Additional Payment</Text>
      </View>

      <ScrollView className="flex-1 px-6 pt-6">
        {/* Warning Banner */}
        <View className="bg-[#FFF3CD] rounded-xl p-4 mb-6 flex-row items-center">
          <AlertTriangle size={24} color="#856404" />
          <View className="ml-3 flex-1">
            <Text className="font-interBold text-[#856404] text-[15px]">Grace Period Expired</Text>
            <Text className="font-inter text-[#856404] text-[13px] mt-1">
              You have exceeded your grace period. An additional charge is required to exit.
            </Text>
          </View>
        </View>

        {/* Charge Breakdown Card */}
        <View className="bg-[#f9f9f9] rounded-xl p-5 mb-6 shadow-sm">
          <Text className="font-interBold text-gray-900 text-[16px] mb-4">Charge Breakdown</Text>

          <View className="flex-row justify-between mb-3 pb-3 border-b border-gray-200">
            <Text className="font-inter text-gray-500">License Plate</Text>
            <Text className="font-interBold text-gray-900">{sessionData.license_plate}</Text>
          </View>
          <View className="flex-row justify-between mb-3 pb-3 border-b border-gray-200">
            <Text className="font-inter text-gray-500">Entry Time</Text>
            <Text className="font-interBold text-gray-900">{formatDate(sessionData.entry_time)}</Text>
          </View>
          <View className="flex-row justify-between mb-3 pb-3 border-b border-gray-200">
            <Text className="font-inter text-gray-500">Original Parking Fee</Text>
            <Text className="font-interBold text-gray-900">RM {originalFee.toFixed(2)}</Text>
          </View>
          <View className="flex-row justify-between mb-3 pb-3 border-b border-gray-200">
            <Text className="font-inter text-gray-500">Total Previously Paid</Text>
            <Text className="font-interBold text-green-600">RM {totalPaid.toFixed(2)}</Text>
          </View>
          <View className="flex-row justify-between mb-3 pb-3 border-b border-gray-200">
            <Text className="font-inter text-gray-500">Grace Exceeded</Text>
            <Text className="font-interBold text-[#dc3545]">{overdueMinutes} minutes</Text>
          </View>
          <View className="flex-row justify-between">
            <Text className="font-inter text-gray-500">Extra Charge</Text>
            <Text className="font-interBold text-[#dc3545]">RM {extraCharge.toFixed(2)}</Text>
          </View>
        </View>

        {/* Total Outstanding */}
        <View className="items-center mb-6">
          <Text className="font-inter text-gray-500 mb-2">Total Outstanding</Text>
          <Text className="font-manrope text-4xl font-bold text-[#dc3545]">
            RM {extraCharge.toFixed(2)}
          </Text>
        </View>

        {/* Payment Method Selection */}
        <Text className="font-inter text-gray-500 mb-4">Choose your payment option</Text>

        {paymentMethods.map((method) => {
          const IconComponent = method.icon;
          const isSelected = selectedMethod === method.id;

          return (
            <TouchableOpacity
              key={method.id}
              activeOpacity={0.8}
              onPress={() => setSelectedMethod(method.id)}
              className={`flex-row items-center p-4 mb-4 rounded-xl border ${
                isSelected ? 'border-[#007BFF] bg-[#F0F7FF]' : 'border-gray-200 bg-white'
              }`}
            >
              <View className={`w-10 h-10 rounded-full items-center justify-center ${isSelected ? 'bg-[#007BFF]/10' : 'bg-gray-100'}`}>
                <IconComponent size={20} color={isSelected ? '#007BFF' : '#666'} />
              </View>
              <Text className={`flex-1 ml-4 font-interBold text-[16px] ${isSelected ? 'text-[#007BFF]' : 'text-gray-800'}`}>
                {method.label}
              </Text>
              {isSelected ? (
                <CheckCircle2 size={24} color="#007BFF" />
              ) : (
                <Circle size={24} color="#ccc" />
              )}
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* Footer Action */}
      <View className="px-6 py-4 bg-white border-t border-gray-100">
        <TouchableOpacity
          className="w-full h-[56px] bg-[#dc3545] rounded-lg items-center justify-center"
          style={{
            shadowColor: '#dc3545',
            shadowOffset: { width: 0, height: 4 },
            shadowOpacity: 0.2,
            shadowRadius: 8,
            elevation: 4,
          }}
          onPress={handlePayAdditional}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text className="font-interBold text-white text-[16px]">Pay Additional Charge</Text>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
}
